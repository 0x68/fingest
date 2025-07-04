"""Cloud storage adapters for fingest."""

from .aws import S3Adapter, aws_bucket_fixture
from .azure import AzureBlobAdapter, azure_blob_fixture
from .base import CloudAdapter, CloudAdapterProtocol
from .gcp import GCSAdapter, gcs_fixture

__all__ = [
    "CloudAdapter",
    "CloudAdapterProtocol",
    "S3Adapter",
    "aws_bucket_fixture",
    "GCSAdapter",
    "gcs_fixture",
    "AzureBlobAdapter",
    "azure_blob_fixture",
]
