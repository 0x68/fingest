"""Fingest - Pytest plugin for data-driven fixtures.

This plugin allows you to easily define data-driven fixtures based on external files.
It supports JSON, CSV, and XML data sources, and can automatically instantiate
Python classes or functions using this data.
"""

from .adapters import (
    AzureBlobAdapter,
    CloudAdapter,
    GCSAdapter,
    S3Adapter,
    aws_bucket_fixture,
    azure_blob_fixture,
    gcs_fixture,
)
from .plugin import data_fixture, register_loader
from .types import BaseFixture, CSVFixture, JSONFixture, XMLFixture

__version__ = "0.1.0"
__author__ = "Tim Fiedler"
__email__ = "tim@0x68.de"

__all__ = [
    "data_fixture",
    "register_loader",
    "BaseFixture",
    "JSONFixture",
    "CSVFixture",
    "XMLFixture",
    "aws_bucket_fixture",
    "gcs_fixture",
    "azure_blob_fixture",
    "CloudAdapter",
    "S3Adapter",
    "GCSAdapter",
    "AzureBlobAdapter",
]
