"""Tests for cloud storage adapters."""

from unittest.mock import patch

import pytest

from fingest import (
    CSVFixture,
    JSONFixture,
    XMLFixture,
    aws_bucket_fixture,
    azure_blob_fixture,
    gcs_fixture,
)
from fingest.adapters.aws import S3Adapter
from fingest.adapters.azure import AzureBlobAdapter
from fingest.adapters.gcp import GCSAdapter


def test_s3_adapter_mock_mode(tmp_path):
    """Test S3Adapter in mock mode loads local file via _parse_content."""
    test_file = tmp_path / "test.json"
    test_file.write_text('{"foo": "bar"}')

    adapter = S3Adapter(bucket="my-bucket", key="test.json", mock=True)
    data = adapter(test_file)
    assert data == {"foo": "bar"}


def test_gcs_adapter_mock_mode(tmp_path):
    """Test GCSAdapter in mock mode loads local file via _parse_content."""
    test_file = tmp_path / "test.csv"
    test_file.write_text("id,name\n1,test")

    adapter = GCSAdapter(bucket="my-bucket", key="test.csv", mock=True)
    data = adapter(test_file)
    assert data == [{"id": "1", "name": "test"}]


def test_azure_adapter_mock_mode(tmp_path):
    """Test AzureBlobAdapter in mock mode loads local file via _parse_content."""
    test_file = tmp_path / "test.xml"
    test_file.write_text("<root/>")

    adapter = AzureBlobAdapter(bucket="my-container", key="test.xml", mock=True)
    data = adapter(test_file)
    assert data.getroot().tag == "root"


def test_adapter_metadata():
    """Test adapter metadata preservation."""
    s3 = S3Adapter(bucket="b", key="k")
    assert s3.bucket == "b"
    assert s3.key == "k"
    assert s3.mock is True


def test_s3_live_loading_import_error():
    """Test S3 live loading raises ImportError if boto3 is missing."""
    adapter = S3Adapter(bucket="b", key="k", mock=False)
    with patch.dict("sys.modules", {"boto3": None}):
        with pytest.raises(ImportError, match="boto3 is required"):
            adapter._load_remote()


def test_gcs_live_loading_import_error():
    """Test GCS live loading raises ImportError if google-cloud-storage is missing."""
    adapter = GCSAdapter(bucket="b", key="k", mock=False)
    with patch.dict("sys.modules", {"google.cloud": None}):
        with pytest.raises(ImportError, match="google-cloud-storage is required"):
            adapter._load_remote()


def test_azure_live_loading_import_error():
    """Test Azure live loading raises ImportError if azure-storage-blob is missing."""
    adapter = AzureBlobAdapter(bucket="b", key="k", mock=False)
    with patch.dict("sys.modules", {"azure.storage.blob": None}):
        with pytest.raises(ImportError, match="azure-storage-blob is required"):
            adapter._load_remote()


def test_aws_bucket_fixture_registration():
    """Test that @aws_bucket_fixture registers a fixture."""
    with patch("fingest.adapters.aws.data_fixture") as mock_df:

        @aws_bucket_fixture(bucket="my-bucket", key="data.json", description="test")
        class MyS3Fixture(JSONFixture):
            pass

        mock_df.assert_called_once()
        args, kwargs = mock_df.call_args
        assert kwargs["file_path"] == "data.json"
        assert kwargs["description"] == "test"
        assert isinstance(kwargs["loader"], S3Adapter)


def test_gcs_fixture_registration():
    """Test that @gcs_fixture registers a fixture."""
    with patch("fingest.adapters.gcp.data_fixture") as mock_df:

        @gcs_fixture(bucket="my-bucket", key="data.csv")
        class MyGCSFixture(CSVFixture):
            pass

        mock_df.assert_called_once()
        args, kwargs = mock_df.call_args
        assert kwargs["file_path"] == "data.csv"
        assert isinstance(kwargs["loader"], GCSAdapter)


def test_azure_blob_fixture_registration():
    """Test that @azure_blob_fixture registers a fixture."""
    with patch("fingest.adapters.azure.data_fixture") as mock_df:

        @azure_blob_fixture(container="my-container", blob="data.xml")
        class MyAzureFixture(XMLFixture):
            pass

        mock_df.assert_called_once()
        args, kwargs = mock_df.call_args
        assert kwargs["file_path"] == "data.xml"
        assert isinstance(kwargs["loader"], AzureBlobAdapter)


def test_gcs_bucket(gcs_bucket):
    assert gcs_bucket == {"Foo": "Bar"}
