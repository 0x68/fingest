"""Base class and protocol for cloud storage adapters."""

import io
from pathlib import Path
from typing import Any, Optional, Protocol, Union, runtime_checkable


@runtime_checkable
class CloudAdapterProtocol(Protocol):
    """Protocol for cloud storage adapters."""

    bucket: str
    key: str
    mock: bool

    def __call__(self, path: Path) -> Any:
        """Execute the loading logic."""
        ...


class CloudAdapter:
    """Base class for cloud storage adapters.

    Acts as a custom loader for fingest fixtures.
    """

    def __init__(self, bucket: str, key: str, mock: bool = True):
        """Initialize the adapter.

        Args:
            bucket: Cloud storage bucket or container name.
            key: Path/key to the object within the bucket.
            mock: If True (default), loads data from the local path provided by fingest.
                 If False, attempts to load from the real cloud provider.
        """
        self.bucket = bucket
        self.key = key
        self.mock = mock

    def __call__(self, path: Path) -> Any:
        """Load data from local or remote source.

        This method is called by fingest's data_fixture when it needs to load data.

        Args:
            path: Local path resolved by fingest (based on fingest_fixture_path).

        Returns:
            Loaded data.
        """
        if self.mock:
            return self._load_local(path)
        return self._load_remote()

    def _load_local(self, path: Path) -> Any:
        """Load data from the local file system.

        This is used for mocking cloud storage endpoints.
        """
        # We import here to avoid circular dependencies
        from fingest.plugin import _load_data

        return _load_data(path)

    def _load_remote(self) -> Any:
        """Load data from the actual cloud provider.

        Must be implemented by subclasses.
        """
        raise NotImplementedError(
            "Remote loading not implemented for base CloudAdapter"
        )

    def _parse_content(
        self, content: Union[bytes, str], extension: Optional[str] = None
    ) -> Any:
        """Parse raw content based on file extension.

        Args:
            content: Raw content (bytes or string).
            extension: File extension (e.g., '.json').
                       If not provided, tries to infer from self.key.

        Returns:
            Parsed data.
        """
        if extension is None:
            extension = Path(self.key).suffix.lower()
        else:
            extension = extension.lower()

        # Normalize extension (remove leading dot if present)
        if extension.startswith("."):
            extension = extension[1:]

        # Convert bytes to string if needed for some parsers
        if isinstance(content, bytes):
            try:
                text_content = content.decode("utf-8")
            except UnicodeDecodeError:
                text_content = ""  # Fallback if not decodable
        else:
            text_content = content

        if extension == "json":
            import json

            return json.loads(text_content)
        elif extension == "csv":
            import csv

            reader = csv.DictReader(io.StringIO(text_content))
            return list(reader)
        elif extension == "xml":
            from lxml import etree

            # etree can handle both bytes and str
            if isinstance(content, str):
                return etree.fromstring(content.encode("utf-8"))
            return etree.fromstring(content)

        return content
