"""Tests for cloud storage adapters."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fingest import (
    aws_bucket_fixture,
    gcs_fixture,
    azure_blob_fixture,
    JSONFixture,
    CSVFixture,
    XMLFixture
)
from fingest.adapters.base import CloudAdapter
from fingest.adapters.aws import S3Adapter
from fingest.adapters.gcp import GCSAdapter
from fingest.adapters.azure import AzureBlobAdapter

class TestCloudAdapters:
    """Test suite for cloud storage adapters in mock mode."""

    def test_s3_adapter_mock_mode(self, tmp_path):
        """Test S3Adapter in mock mode loads local file."""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"foo": "bar"}')
        
        adapter = S3Adapter(bucket="my-bucket", key="test.json", mock=True)
        # We need to mock fingest.plugin._load_data for this unit test
        with patch("fingest.plugin._load_data") as mock_load:
            mock_load.return_value = {"foo": "bar"}
            data = adapter(test_file)
            assert data == {"foo": "bar"}
            mock_load.assert_called_once_with(test_file)

    def test_gcs_adapter_mock_mode(self, tmp_path):
        """Test GCSAdapter in mock mode loads local file."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("id,name\n1,test")
        
        adapter = GCSAdapter(bucket="my-bucket", key="test.csv", mock=True)
        with patch("fingest.plugin._load_data") as mock_load:
            mock_load.return_value = [{"id": "1", "name": "test"}]
            data = adapter(test_file)
            assert data == [{"id": "1", "name": "test"}]
            mock_load.assert_called_once_with(test_file)

    def test_azure_adapter_mock_mode(self, tmp_path):
        """Test AzureBlobAdapter in mock mode loads local file."""
        test_file = tmp_path / "test.xml"
        test_file.write_text("<root/>")
        
        adapter = AzureBlobAdapter(bucket="my-container", key="test.xml", mock=True)
        with patch("fingest.plugin._load_data") as mock_load:
            mock_load.return_value = MagicMock() # Mock xml tree
            data = adapter(test_file)
            assert data is not None
            mock_load.assert_called_once_with(test_file)

    def test_adapter_metadata(self):
        """Test adapter metadata preservation."""
        s3 = S3Adapter(bucket="b", key="k")
        assert s3.bucket == "b"
        assert s3.key == "k"
        assert s3.mock is True

    def test_s3_live_loading_import_error(self):
        """Test S3 live loading raises ImportError if boto3 is missing."""
        adapter = S3Adapter(bucket="b", key="k", mock=False)
        with patch.dict("sys.modules", {"boto3": None}):
            with pytest.raises(ImportError, match="boto3 is required"):
                adapter._load_remote()

    def test_gcs_live_loading_import_error(self):
        """Test GCS live loading raises ImportError if google-cloud-storage is missing."""
        adapter = GCSAdapter(bucket="b", key="k", mock=False)
        with patch.dict("sys.modules", {"google.cloud": None}):
            with pytest.raises(ImportError, match="google-cloud-storage is required"):
                adapter._load_remote()

    def test_azure_live_loading_import_error(self):
        """Test Azure live loading raises ImportError if azure-storage-blob is missing."""
        adapter = AzureBlobAdapter(bucket="b", key="k", mock=False)
        with patch.dict("sys.modules", {"azure.storage.blob": None}):
            with pytest.raises(ImportError, match="azure-storage-blob is required"):
                adapter._load_remote()

class TestCloudDecorators:
    """Test cloud fixture decorators."""

    def test_aws_bucket_fixture_registration(self):
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

    def test_gcs_fixture_registration(self):
        """Test that @gcs_fixture registers a fixture."""
        with patch("fingest.adapters.gcp.data_fixture") as mock_df:
            @gcs_fixture(bucket="my-bucket", key="data.csv")
            class MyGCSFixture(CSVFixture):
                pass
            
            mock_df.assert_called_once()
            args, kwargs = mock_df.call_args
            assert kwargs["file_path"] == "data.csv"
            assert isinstance(kwargs["loader"], GCSAdapter)

    def test_azure_blob_fixture_registration(self):
        """Test that @azure_blob_fixture registers a fixture."""
        with patch("fingest.adapters.azure.data_fixture") as mock_df:
            @azure_blob_fixture(container="my-container", blob="data.xml")
            class MyAzureFixture(XMLFixture):
                pass
            
            mock_df.assert_called_once()
            args, kwargs = mock_df.call_args
            assert kwargs["file_path"] == "data.xml"
            assert isinstance(kwargs["loader"], AzureBlobAdapter)
