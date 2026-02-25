"""GCP GCS adapter and fixture decorator."""

from collections.abc import Callable
from typing import Any

from fingest.adapters.base import CloudAdapter
from fingest.plugin import data_fixture


class GCSAdapter(CloudAdapter):
    """Adapter for Google Cloud Storage buckets."""

    def _load_remote(self) -> Any:
        """Load data from GCS using google-cloud-storage."""
        try:
            from google.cloud import storage
        except ImportError:
            raise ImportError(
                "google-cloud-storage is required for live GCS loading. "
                "Install it with: pip install google-cloud-storage"
            ) from None

        client = storage.Client()
        bucket = client.bucket(self.bucket)
        blob = bucket.blob(self.key)
        content = blob.download_as_bytes()

        return self._parse_content(content)


def gcs_fixture(
    bucket: str,
    key: str,
    description: str = "",
    mock: bool = True,
) -> Callable:
    """Decorator for GCS bucket fixtures.

    Args:
        bucket: Name of the GCS bucket.
        key: Path/key of the blob in the bucket.
        description: Optional fixture description.
        mock: If True (default), loads from the local file mapping.

    Returns:
        The decorated class or function.
    """
    loader = GCSAdapter(bucket, key, mock=mock)

    def decorator(obj: Any) -> Any:
        return data_fixture(file_path=key, description=description, loader=loader)(obj)

    return decorator
