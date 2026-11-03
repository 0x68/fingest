"""In-memory simulations of AWS S3, Google Cloud Storage and Azure Blob Storage.

Submodules are imported lazily, so plain ``@data_fixture`` users never pay for
the cloud SDK imports.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

_EXPORTS = {
    "FakeAzureBlob": "fingest.cloud.azure",
    "FakeCloud": "fingest.cloud.base",
    "FakeGCS": "fingest.cloud.gcs",
    "FakeS3": "fingest.cloud.s3",
    "aws_bucket_fixture": "fingest.cloud.decorators",
    "azure_blob_fixture": "fingest.cloud.decorators",
    "gcs_fixture": "fingest.cloud.decorators",
    "BucketAlreadyExists": "fingest.cloud.store",
    "BucketNotEmpty": "fingest.cloud.store",
    "BucketNotFound": "fingest.cloud.store",
    "ObjectNotFound": "fingest.cloud.store",
    "ObjectStore": "fingest.cloud.store",
    "StorageError": "fingest.cloud.store",
    "StoredObject": "fingest.cloud.store",
}

__all__ = sorted(_EXPORTS)

if TYPE_CHECKING:
    from fingest.cloud.azure import FakeAzureBlob
    from fingest.cloud.base import FakeCloud
    from fingest.cloud.decorators import (
        aws_bucket_fixture,
        azure_blob_fixture,
        gcs_fixture,
    )
    from fingest.cloud.gcs import FakeGCS
    from fingest.cloud.s3 import FakeS3
    from fingest.cloud.store import (
        BucketAlreadyExists,
        BucketNotEmpty,
        BucketNotFound,
        ObjectNotFound,
        ObjectStore,
        StorageError,
        StoredObject,
    )


def __getattr__(name: str) -> Any:
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module), name)
