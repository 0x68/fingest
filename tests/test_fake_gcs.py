"""FakeGCS exercised through the real google-cloud-storage entry points."""

import pytest

storage = pytest.importorskip("google.cloud.storage")
from google.api_core.exceptions import Conflict, NotFound, PreconditionFailed  # noqa: E402
from google.cloud.storage import Blob, Client  # noqa: E402  (imported before activation)

from fingest.cloud.gcs import FakeGCS, FakeGCSClient  # noqa: E402


@pytest.fixture
def client(fake_gcs):
    return storage.Client(project="test")


def test_seeded_and_read(client):
    blob = client.bucket("analytics").blob("events/day1.jsonl")
    assert blob.size is None  # like the real SDK: not fetched yet
    text = blob.download_as_text()
    assert '"event":"click"' in text
    assert blob.size == len(text)


def test_preimported_classes_are_faked(fake_gcs):
    fake_gcs.put("b", "k.txt", "v")
    assert isinstance(Client(), FakeGCSClient)
    # from_uri() is the newer name; older releases only have from_string()
    from_uri = getattr(Blob, "from_uri", None) or Blob.from_string
    assert from_uri("gs://b/k.txt", client=Client()).download_as_bytes() == b"v"


def test_upload_variants(client, fake_gcs, tmp_path):
    bucket = client.bucket("analytics")
    bucket.blob("s.txt").upload_from_string("hello")
    assert fake_gcs.get("analytics", "s.txt").content_type == "text/plain"

    src = tmp_path / "d.json"
    src.write_text('{"a": 1}')
    bucket.blob("d.json").upload_from_filename(str(src))
    assert fake_gcs.get("analytics", "d.json").content_type == "application/json"

    with bucket.blob("w.txt").open("w") as fh:
        fh.write("streamed")
    assert fake_gcs.get_text("analytics", "w.txt") == "streamed"
    with bucket.blob("w.txt").open("r") as fh:
        assert fh.read() == "streamed"

    blob = bucket.blob("meta.txt")
    blob.metadata = {"k": "v"}
    blob.upload_from_string(b"x", content_type="application/x-custom")
    fetched = bucket.get_blob("meta.txt")
    assert fetched.metadata == {"k": "v"}
    assert fetched.content_type == "application/x-custom"
    assert fetched.md5_hash and fetched.generation


def test_download_variants(client, tmp_path):
    blob = client.bucket("analytics").blob("products.csv")
    data = blob.download_as_bytes()
    assert blob.download_as_bytes(start=0, end=1) == data[:2]
    target = tmp_path / "out.csv"
    blob.download_to_filename(str(target))
    assert target.read_bytes() == data


def test_list_blobs_prefix_delimiter_glob(client, fake_gcs):
    fake_gcs.put("analytics", "events/day2.jsonl", "")
    fake_gcs.put("analytics", "events/raw/x.bin", b"")
    names = [b.name for b in client.list_blobs("analytics", prefix="events/")]
    assert names == ["events/day1.jsonl", "events/day2.jsonl", "events/raw/x.bin"]

    it = client.list_blobs("analytics", prefix="events/", delimiter="/")
    assert [b.name for b in it] == ["events/day1.jsonl", "events/day2.jsonl"]
    assert it.prefixes == {"events/raw/"}

    globbed = client.bucket("analytics").list_blobs(match_glob="**.jsonl")
    assert [b.name for b in globbed] == ["events/day1.jsonl", "events/day2.jsonl"]
    assert len(list(client.list_blobs("analytics", max_results=1))) == 1


def test_generation_preconditions(client):
    blob = client.bucket("analytics").blob("once.txt")
    blob.upload_from_string("first", if_generation_match=0)
    with pytest.raises(PreconditionFailed):
        blob.upload_from_string("second", if_generation_match=0)
    blob.upload_from_string("second", if_generation_match=blob.generation)
    assert blob.download_as_text() == "second"


def test_not_found_and_conflict(client):
    with pytest.raises(NotFound, match="No such object: analytics/missing"):
        client.bucket("analytics").blob("missing").download_as_bytes()
    with pytest.raises(NotFound):
        client.get_bucket("missing")
    assert client.lookup_bucket("missing") is None
    assert client.bucket("analytics").get_blob("missing") is None
    with pytest.raises(NotFound):
        client.bucket("missing").blob("k").upload_from_string("x")
    with pytest.raises(Conflict):
        client.create_bucket("analytics")
    with pytest.raises(Conflict):
        client.bucket("analytics").delete()


def test_bucket_management(client, fake_gcs):
    client.create_bucket("fresh")
    assert [b.name for b in client.list_buckets()] == ["analytics", "fresh"]
    source = client.bucket("analytics").blob("products.csv")
    copied = client.bucket("analytics").copy_blob(
        source, client.bucket("fresh"), "p.csv"
    )
    assert copied.size == fake_gcs.get("analytics", "products.csv").size
    client.bucket("fresh").rename_blob(copied, "renamed.csv")
    assert fake_gcs.keys("fresh") == ["renamed.csv"]
    client.bucket("fresh").delete(force=True)
    assert not client.bucket("fresh").exists()


def test_client_without_sdk_patching():
    fake = FakeGCS()
    fake.put("b", "k", b"v")
    assert fake.client().bucket("b").blob("k").download_as_bytes() == b"v"
    with pytest.raises(RuntimeError, match="not bound"):
        FakeGCSClient()


def test_stop_restores_real_client():
    with FakeGCS():
        assert isinstance(storage.Client(project="p"), FakeGCSClient)
    assert type(storage.Client.create_anonymous_client()) is storage.Client
