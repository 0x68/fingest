"""FakeS3 exercised through the real boto3/botocore SDK."""

import io

import pytest

boto3 = pytest.importorskip("boto3")
from botocore.client import BaseClient  # noqa: E402
from botocore.exceptions import ClientError, ParamValidationError  # noqa: E402

from fingest.cloud.s3 import FakeS3  # noqa: E402


@pytest.fixture
def s3(fake_s3):
    return boto3.client("s3", region_name="eu-central-1")


def test_seeded_from_directory(s3, fake_s3):
    assert fake_s3.buckets() == ["reports"]
    body = s3.get_object(Bucket="reports", Key="2026/11/sales.csv")["Body"].read()
    assert body.startswith(b"id,amount")


def test_put_get_head_delete_roundtrip(s3, fake_s3):
    s3.put_object(
        Bucket="reports",
        Key="new.json",
        Body=b'{"a": 1}',
        ContentType="application/json",
        Metadata={"owner": "qa"},
    )
    head = s3.head_object(Bucket="reports", Key="new.json")
    assert head["ContentLength"] == 8
    assert head["ContentType"] == "application/json"
    assert head["Metadata"] == {"owner": "qa"}
    got = s3.get_object(Bucket="reports", Key="new.json")
    assert got["ETag"] == head["ETag"]
    assert got["Body"].read() == b'{"a": 1}'
    assert fake_s3.get_json("reports", "new.json") == {"a": 1}

    s3.delete_object(Bucket="reports", Key="new.json")
    assert not fake_s3.exists("reports", "new.json")


def test_errors_are_real_modeled_exceptions(s3):
    with pytest.raises(s3.exceptions.NoSuchKey):
        s3.get_object(Bucket="reports", Key="missing")
    with pytest.raises(s3.exceptions.NoSuchBucket):
        s3.get_object(Bucket="missing", Key="k")
    with pytest.raises(ClientError) as exc:
        s3.head_object(Bucket="reports", Key="missing")
    assert exc.value.response["Error"]["Code"] == "404"
    assert exc.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404
    with pytest.raises(s3.exceptions.BucketAlreadyOwnedByYou):
        s3.create_bucket(Bucket="reports")
    with pytest.raises(ClientError, match="BucketNotEmpty"):
        s3.delete_bucket(Bucket="reports")


def test_parameters_validated_against_service_model(s3):
    with pytest.raises(ParamValidationError):
        s3.put_object(Bucket="reports")


def test_range_requests(s3, fake_s3):
    fake_s3.put("reports", "r.bin", b"0123456789")
    get = s3.get_object
    assert (
        get(Bucket="reports", Key="r.bin", Range="bytes=2-4")["Body"].read() == b"234"
    )
    assert get(Bucket="reports", Key="r.bin", Range="bytes=7-")["Body"].read() == b"789"
    assert get(Bucket="reports", Key="r.bin", Range="bytes=-2")["Body"].read() == b"89"
    resp = get(Bucket="reports", Key="r.bin", Range="bytes=8-100")
    assert resp["ContentRange"] == "bytes 8-9/10"
    with pytest.raises(ClientError, match="InvalidRange"):
        get(Bucket="reports", Key="r.bin", Range="bytes=50-")


def test_conditional_get(s3, fake_s3):
    etag = s3.put_object(Bucket="reports", Key="c", Body=b"x")["ETag"]
    assert s3.get_object(Bucket="reports", Key="c", IfMatch=etag)["Body"].read() == b"x"
    with pytest.raises(ClientError, match="PreconditionFailed"):
        s3.get_object(Bucket="reports", Key="c", IfMatch='"nope"')


def test_list_objects_v2_with_delimiter_and_pagination(s3, fake_s3):
    for i in range(5):
        fake_s3.put("reports", f"many/{i:02}.txt", b"")
    paginator = s3.get_paginator("list_objects_v2")
    pages = list(
        paginator.paginate(
            Bucket="reports", Prefix="many/", PaginationConfig={"PageSize": 2}
        )
    )
    assert len(pages) == 3
    assert [o["Key"] for p in pages for o in p["Contents"]] == [
        f"many/{i:02}.txt" for i in range(5)
    ]

    top = s3.list_objects_v2(Bucket="reports", Delimiter="/")
    assert [o["Key"] for o in top["Contents"]] == ["users.json"]
    assert [p["Prefix"] for p in top["CommonPrefixes"]] == [
        "2026/",
        "archive/",
        "many/",
    ]

    paged_prefixes = [
        cp["Prefix"]
        for page in paginator.paginate(
            Bucket="reports", Delimiter="/", PaginationConfig={"PageSize": 1}
        )
        for cp in page.get("CommonPrefixes", [])
    ]
    assert paged_prefixes == ["2026/", "archive/", "many/"]

    empty = s3.list_objects_v2(Bucket="reports", Prefix="nothing/")
    assert "Contents" not in empty
    assert empty["KeyCount"] == 0


def test_list_objects_v1_and_resource_api(fake_s3):
    resource = boto3.resource("s3", region_name="us-east-1")
    bucket = resource.Bucket("reports")
    assert sorted(o.key for o in bucket.objects.filter(Prefix="archive/")) == [
        "archive/old.txt"
    ]
    obj = resource.Object("reports", "archive/old.txt")
    assert obj.content_length == 4
    assert obj.get()["Body"].read() == b"old\n"
    assert [b.name for b in resource.buckets.all()] == ["reports"]


def test_copy_and_batch_delete(s3, fake_s3):
    s3.copy_object(
        Bucket="reports",
        Key="copy.json",
        CopySource={"Bucket": "reports", "Key": "users.json"},
    )
    s3.copy({"Bucket": "reports", "Key": "users.json"}, "reports", "managed-copy.json")
    assert fake_s3.get_bytes("reports", "copy.json") == fake_s3.get_bytes(
        "reports", "managed-copy.json"
    )
    resp = s3.delete_objects(
        Bucket="reports",
        Delete={"Objects": [{"Key": "copy.json"}, {"Key": "managed-copy.json"}]},
    )
    assert len(resp["Deleted"]) == 2
    assert not fake_s3.exists("reports", "copy.json")


def test_upload_download_file_including_multipart(s3, fake_s3, tmp_path):
    payload = bytes(range(256)) * (40 * 1024)  # 10 MiB > 8 MiB multipart threshold
    src = tmp_path / "big.bin"
    src.write_bytes(payload)
    s3.upload_file(str(src), "reports", "big.bin")
    stored = fake_s3.get("reports", "big.bin")
    assert stored.size == len(payload)
    assert stored.etag.endswith("-2")
    assert "CompleteMultipartUpload" in {op for op, _ in fake_s3.calls}

    dst = tmp_path / "out.bin"
    s3.download_file("reports", "big.bin", str(dst))
    assert dst.read_bytes() == payload

    buf = io.BytesIO()
    s3.download_fileobj("reports", "users.json", buf)
    assert buf.getvalue() == fake_s3.get_bytes("reports", "users.json")


def test_abort_multipart(s3):
    upload = s3.create_multipart_upload(Bucket="reports", Key="m")
    assert s3.list_multipart_uploads(Bucket="reports")["Uploads"]
    s3.abort_multipart_upload(Bucket="reports", Key="m", UploadId=upload["UploadId"])
    with pytest.raises(s3.exceptions.NoSuchUpload):
        s3.upload_part(
            Bucket="reports",
            Key="m",
            UploadId=upload["UploadId"],
            PartNumber=1,
            Body=b"",
        )


def test_client_created_before_fake_is_intercepted(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "x")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "x")
    client = boto3.client("s3", region_name="us-east-1")
    with FakeS3() as fake:
        fake.put("early", "k", b"v")
        assert client.get_object(Bucket="early", Key="k")["Body"].read() == b"v"


def test_unsupported_operation_is_explicit(s3):
    with pytest.raises(NotImplementedError, match="PutBucketPolicy"):
        s3.put_bucket_policy(Bucket="reports", Policy="{}")


def test_other_services_are_not_intercepted(monkeypatch):
    seen = []

    def recorder(client, operation, params):
        seen.append((client.meta.service_model.service_name, operation))
        return {}

    monkeypatch.setattr(BaseClient, "_make_api_call", recorder)
    with FakeS3() as fake:
        boto3.client("sqs", region_name="us-east-1").list_queues()
        boto3.client("s3", region_name="us-east-1").list_buckets()
    assert seen == [("sqs", "ListQueues")]
    assert [op for op, _ in fake.calls] == ["ListBuckets"]


def test_fixture_uses_dummy_credentials(fake_s3):
    import os

    assert os.environ["AWS_ACCESS_KEY_ID"] == "fingest"
    assert "AWS_PROFILE" not in os.environ


def test_only_one_active_fake_per_provider(fake_s3):
    with pytest.raises(RuntimeError, match="already active"):
        FakeS3().start()


def test_stop_restores_botocore():
    original = BaseClient._make_api_call
    with FakeS3():
        assert BaseClient._make_api_call is not original
    assert BaseClient._make_api_call is original


def test_isolation_between_tests_part1(fake_s3):
    fake_s3.put("reports", "leak.txt", "x")
    fake_s3.delete("reports", "users.json")


def test_isolation_between_tests_part2(fake_s3):
    assert not fake_s3.exists("reports", "leak.txt")
    assert fake_s3.exists("reports", "users.json")
