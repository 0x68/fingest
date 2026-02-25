"""Azure Blob adapter and fixture decorator."""

from collections.abc import Callable
from typing import Any

from fingest.adapters.base import CloudAdapter
from fingest.plugin import data_fixture


class AzureBlobAdapter(CloudAdapter):
    """Adapter for Azure Blob Storage."""

    def _load_remote(self) -> Any:
        """Load data from Azure Blob Storage using azure-storage-blob."""
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            raise ImportError(
                "azure-storage-blob is required for live Azure loading. "
                "Install it with: pip install azure-storage-blob"
            ) from None

        # Assumes connection string is in environment or managed identity
        # This is a simplified implementation for the remote part
        import os

        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not conn_str:
            raise ValueError(
                "AZURE_STORAGE_CONNECTION_STRING environment variable not set"
            )

        service_client = BlobServiceClient.from_connection_string(conn_str)
        blob_client = service_client.get_blob_client(
            container=self.bucket, blob=self.key
        )
        content = blob_client.download_blob().readall()

        return self._parse_content(content)


def azure_blob_fixture(
    container: str,
    blob: str,
    description: str = "",
    mock: bool = True,
) -> Callable:
    """Decorator for Azure Blob fixtures.

    Args:
        container: Name of the Azure Storage container.
        blob: Path/name of the blob.
        description: Optional fixture description.
        mock: If True (default), loads from the local file mapping.

    Returns:
        The decorated class or function.
    """
    loader = AzureBlobAdapter(container, blob, mock=mock)

    def decorator(obj: Any) -> Any:
        return data_fixture(file_path=blob, description=description, loader=loader)(obj)

    return decorator
