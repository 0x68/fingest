"""The README's headline example, kept honest."""

import pytest

boto3 = pytest.importorskip("boto3")
import botocore.exceptions  # noqa: E402


def total_sales(bucket: str, month: str) -> float:
    s3 = boto3.client("s3")
    body = s3.get_object(Bucket=bucket, Key=f"{month}/sales.csv")["Body"].read()
    rows = body.decode().splitlines()[1:]
    return sum(float(r.split(",")[1]) for r in rows)


def archive(bucket: str, key: str) -> None:
    s3 = boto3.client("s3")
    s3.copy_object(Bucket=bucket, Key=f"archive/{key}", CopySource=f"{bucket}/{key}")
    s3.delete_object(Bucket=bucket, Key=key)


def test_total_sales(fake_s3):
    assert total_sales("reports", "2026/11") == 109.5


def test_archive(fake_s3):
    archive("reports", "users.json")
    assert fake_s3.exists("reports", "archive/users.json")
    assert not fake_s3.exists("reports", "users.json")


def test_empty_month(fake_s3):
    fake_s3.put("reports", "2026/12/sales.csv", "id,amount\n")
    assert total_sales("reports", "2026/12") == 0


def test_missing_file(fake_s3):
    with pytest.raises(botocore.exceptions.ClientError, match="NoSuchKey"):
        total_sales("reports", "1999/01")
