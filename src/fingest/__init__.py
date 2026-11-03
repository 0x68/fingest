"""fingest — data-driven pytest fixtures and local cloud storage simulation.

* ``@data_fixture`` turns JSON/CSV/XML (or any registered format) files into
  pytest fixtures.
* ``fake_s3``, ``fake_gcs`` and ``fake_azure_blob`` simulate cloud object
  storage in memory, seeded from local folders, so code using boto3,
  google-cloud-storage or azure-storage-blob runs unchanged in tests.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

from fingest.cloud.decorators import aws_bucket_fixture, azure_blob_fixture, gcs_fixture
from fingest.cloud.store import ObjectStore
from fingest.fixtures import data_fixture
from fingest.loaders import register_loader, register_parser
from fingest.types import BaseFixture, CSVFixture, JSONFixture, XMLFixture

try:
    __version__ = version("fingest")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = [
    "BaseFixture",
    "CSVFixture",
    "FakeAzureBlob",
    "FakeGCS",
    "FakeS3",
    "JSONFixture",
    "ObjectStore",
    "XMLFixture",
    "aws_bucket_fixture",
    "azure_blob_fixture",
    "data_fixture",
    "gcs_fixture",
    "register_loader",
    "register_parser",
]

if TYPE_CHECKING:
    from fingest.cloud.azure import FakeAzureBlob
    from fingest.cloud.gcs import FakeGCS
    from fingest.cloud.s3 import FakeS3

_LAZY = {
    "FakeS3": "fingest.cloud.s3",
    "FakeGCS": "fingest.cloud.gcs",
    "FakeAzureBlob": "fingest.cloud.azure",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        import importlib

        return getattr(importlib.import_module(_LAZY[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
