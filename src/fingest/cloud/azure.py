"""Azure Blob Storage simulation.

:class:`FakeAzureBlob` redirects construction of
``azure.storage.blob.BlobServiceClient``, ``ContainerClient`` and ``BlobClient``
(including ``from_connection_string`` & co.) to in-memory look-alikes while
active, however the classes were imported.
Containers map to buckets of the shared :class:`ObjectStore`. All storage
accounts share one namespace, and credentials are accepted and ignored.

Errors are the real ``azure.core.exceptions`` (``ResourceNotFoundError``,
``ResourceExistsError``) with ``error_code`` and ``status_code`` populated.
Only the synchronous clients are simulated, not ``azure.storage.blob.aio``.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import IO, Any, ClassVar
from urllib.parse import unquote, urlparse

from fingest.cloud.base import FakeCloud
from fingest.cloud.store import (
    BucketAlreadyExists,
    BucketNotFound,
    ObjectStore,
    StoredObject,
    to_bytes,
)

try:  # pragma: no cover - depends on installed extras
    from azure.core.exceptions import (
        HttpResponseError,
        ResourceExistsError,
        ResourceNotFoundError,
    )
except ImportError:  # pragma: no cover

    class HttpResponseError(Exception):  # type: ignore[no-redef]
        def __init__(self, message: str | None = None, **kwargs: Any) -> None:
            super().__init__(message)
            self.message = message
            self.status_code: int | None = None

    class ResourceNotFoundError(HttpResponseError):  # type: ignore[no-redef]
        pass

    class ResourceExistsError(HttpResponseError):  # type: ignore[no-redef]
        pass


try:  # pragma: no cover
    from azure.storage.blob import ContentSettings
except ImportError:  # pragma: no cover

    class ContentSettings:  # type: ignore[no-redef]
        def __init__(self, content_type: str | None = None, **kwargs: Any) -> None:
            self.content_type = content_type
            for key, value in kwargs.items():
                setattr(self, key, value)


DEFAULT_ACCOUNT = "fingest"


def _error(cls: type[HttpResponseError], code: str, status: int, message: str) -> Any:
    exc = cls(message=f"{message}\nErrorCode:{code}")
    exc.error_code = code  # type: ignore[attr-defined]
    exc.status_code = status
    exc.reason = message
    return exc


def _container_not_found(container: str) -> Any:
    return _error(
        ResourceNotFoundError,
        "ContainerNotFound",
        404,
        f"The specified container does not exist. Container: {container}",
    )


def _blob_not_found(container: str, blob: str) -> Any:
    return _error(
        ResourceNotFoundError,
        "BlobNotFound",
        404,
        f"The specified blob does not exist. Blob: {container}/{blob}",
    )


def _account_from_conn_str(conn_str: str) -> tuple[str, str]:
    parts = dict(
        part.split("=", 1)
        for part in conn_str.strip().strip(";").split(";")
        if "=" in part
    )
    if "BlobEndpoint" in parts:
        url = parts["BlobEndpoint"].rstrip("/")
        return url, urlparse(url).netloc.split(".")[0]
    name = parts.get("AccountName", DEFAULT_ACCOUNT)
    suffix = parts.get("EndpointSuffix", "core.windows.net")
    protocol = parts.get("DefaultEndpointsProtocol", "https")
    return f"{protocol}://{name}.blob.{suffix}", name


def _split_url(url: str) -> tuple[str, list[str]]:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    account_url = f"{parsed.scheme}://{parsed.netloc}"
    path = [unquote(p) for p in parsed.path.split("/") if p]
    # Azurite-style URLs carry the account as the first path segment.
    if re.match(r"^(127\.0\.0\.1|localhost)(:\d+)?$", parsed.netloc) and path:
        account_url += f"/{path.pop(0)}"
    return account_url, path


class BlobProperties:
    """Subset of ``azure.storage.blob.BlobProperties`` (attribute & item access)."""

    def __init__(self, container: str, obj: StoredObject) -> None:
        self.name = obj.key
        self.container = container
        self.size = obj.size
        self.etag = f'"{obj.etag}"'
        self.last_modified: datetime = obj.last_modified
        self.creation_time: datetime = obj.last_modified
        self.metadata = dict(obj.metadata)
        self.content_settings = ContentSettings(content_type=obj.content_type)
        self.blob_type = "BlockBlob"
        self.snapshot = None
        self.deleted = False

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __repr__(self) -> str:
        return f"BlobProperties(name={self.name!r}, container={self.container!r})"


class BlobPrefix:
    """A virtual directory yielded by ``walk_blobs``."""

    def __init__(self, container: str, prefix: str) -> None:
        self.name = prefix
        self.prefix = prefix
        self.container = container

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __repr__(self) -> str:
        return f"BlobPrefix(name={self.name!r})"


class ContainerProperties:
    def __init__(self, name: str, last_modified: datetime, metadata: dict[str, str]):
        self.name = name
        self.last_modified = last_modified
        self.metadata = metadata

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __repr__(self) -> str:
        return f"ContainerProperties(name={self.name!r})"


class StorageStreamDownloader:
    """Stand-in for the object returned by ``download_blob()``."""

    def __init__(
        self, properties: BlobProperties, data: bytes, encoding: str | None
    ) -> None:
        self.name = properties.name
        self.container = properties.container
        self.properties = properties
        self.size = len(data)
        self._data = data
        self._encoding = encoding

    def readall(self) -> Any:
        return self._data.decode(self._encoding) if self._encoding else self._data

    def read(self, size: int = -1) -> Any:
        return self.readall()

    def content_as_bytes(self, max_concurrency: int = 1) -> bytes:
        return self._data

    def content_as_text(self, max_concurrency: int = 1, encoding: str = "UTF-8") -> str:
        return self._data.decode(encoding)

    def readinto(self, stream: IO[bytes]) -> int:
        stream.write(self._data)
        return len(self._data)

    download_to_stream = readinto

    def chunks(self) -> Iterator[bytes]:
        yield self._data


class _Bound:
    """Common store resolution for the three fake clients."""

    _default_store: ClassVar[ObjectStore | None] = None

    def _init_store(self, store: ObjectStore | None) -> None:
        resolved = store if store is not None else type(self)._default_store
        if resolved is None:
            raise RuntimeError(
                "fingest Azure fake is not bound to a store; use the fake_azure_blob "
                "fixture or FakeAzureBlob().service_client()"
            )
        self._store = resolved


class FakeBlobServiceClient(_Bound):
    """Stand-in for ``azure.storage.blob.BlobServiceClient``."""

    def __init__(
        self,
        account_url: str = f"https://{DEFAULT_ACCOUNT}.blob.core.windows.net",
        credential: Any = None,
        *,
        _store: ObjectStore | None = None,
        **kwargs: Any,
    ) -> None:
        self._init_store(_store)
        self.url, _ = _split_url(account_url)
        self.primary_endpoint = self.url
        self.account_name = urlparse(self.url).netloc.split(".")[0]
        self.credential = credential

    @classmethod
    def from_connection_string(
        cls, conn_str: str, credential: Any = None, **kwargs: Any
    ) -> FakeBlobServiceClient:
        url, _ = _account_from_conn_str(conn_str)
        return cls(url, credential, **kwargs)

    def _container(self, container: Any) -> FakeContainerClient:
        name = getattr(container, "name", container)
        return FakeContainerClient(self.url, name, _store=self._store)

    def get_container_client(self, container: Any) -> FakeContainerClient:
        return self._container(container)

    def get_blob_client(
        self, container: Any, blob: Any, snapshot: Any = None, **kwargs: Any
    ) -> FakeBlobClient:
        return FakeBlobClient(
            self.url,
            getattr(container, "name", container),
            getattr(blob, "name", blob),
            _store=self._store,
        )

    def create_container(
        self, name: str, metadata: dict[str, str] | None = None, **kwargs: Any
    ) -> FakeContainerClient:
        client = self._container(name)
        client.create_container(metadata=metadata)
        return client

    def delete_container(self, container: Any, **kwargs: Any) -> None:
        self._container(container).delete_container()

    def list_containers(
        self,
        name_starts_with: str | None = None,
        include_metadata: bool = False,
        **kwargs: Any,
    ) -> Iterator[ContainerProperties]:
        return iter(
            [
                ContainerProperties(b.name, b.created, dict(b.metadata))
                for b in self._store.buckets()
                if b.name.startswith(name_starts_with or "")
            ]
        )

    def close(self) -> None:
        pass

    def __enter__(self) -> FakeBlobServiceClient:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class FakeContainerClient(_Bound):
    """Stand-in for ``azure.storage.blob.ContainerClient``."""

    def __init__(
        self,
        account_url: str,
        container_name: str,
        credential: Any = None,
        *,
        _store: ObjectStore | None = None,
        **kwargs: Any,
    ) -> None:
        self._init_store(_store)
        self.account_url, _ = _split_url(account_url)
        self.container_name = container_name
        self.url = f"{self.account_url}/{container_name}"
        self.credential = credential

    @classmethod
    def from_connection_string(
        cls, conn_str: str, container_name: str, credential: Any = None, **kwargs: Any
    ) -> FakeContainerClient:
        url, _ = _account_from_conn_str(conn_str)
        return cls(url, container_name, credential, **kwargs)

    @classmethod
    def from_container_url(
        cls, container_url: str, credential: Any = None, **kwargs: Any
    ) -> FakeContainerClient:
        account_url, path = _split_url(container_url)
        if not path:
            raise ValueError(f"Invalid container URL: {container_url}")
        return cls(account_url, path[0], credential, **kwargs)

    def _require(self) -> None:
        if not self._store.has_bucket(self.container_name):
            raise _container_not_found(self.container_name)

    def exists(self, **kwargs: Any) -> bool:
        return self._store.has_bucket(self.container_name)

    def create_container(
        self, metadata: dict[str, str] | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        try:
            bucket = self._store.create_bucket(self.container_name)
        except BucketAlreadyExists:
            raise _error(
                ResourceExistsError,
                "ContainerAlreadyExists",
                409,
                "The specified container already exists.",
            ) from None
        bucket.metadata.update(metadata or {})
        return {"etag": None, "last_modified": bucket.created}

    def delete_container(self, **kwargs: Any) -> None:
        try:
            self._store.delete_bucket(self.container_name, force=True)
        except BucketNotFound:
            raise _container_not_found(self.container_name) from None

    def get_container_properties(self, **kwargs: Any) -> ContainerProperties:
        self._require()
        bucket = self._store.bucket(self.container_name)
        return ContainerProperties(bucket.name, bucket.created, dict(bucket.metadata))

    def get_blob_client(
        self, blob: Any, snapshot: Any = None, **kwargs: Any
    ) -> FakeBlobClient:
        return FakeBlobClient(
            self.account_url,
            self.container_name,
            getattr(blob, "name", blob),
            _store=self._store,
        )

    def upload_blob(
        self,
        name: Any,
        data: Any,
        blob_type: Any = "BlockBlob",
        length: int | None = None,
        metadata: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> FakeBlobClient:
        client = self.get_blob_client(name)
        client.upload_blob(data, blob_type, length, metadata, **kwargs)
        return client

    def download_blob(
        self,
        blob: Any,
        offset: int | None = None,
        length: int | None = None,
        **kwargs: Any,
    ) -> StorageStreamDownloader:
        return self.get_blob_client(blob).download_blob(offset, length, **kwargs)

    def delete_blob(self, blob: Any, **kwargs: Any) -> None:
        self.get_blob_client(blob).delete_blob()

    def delete_blobs(self, *blobs: Any, **kwargs: Any) -> Iterator[None]:
        for blob in blobs:
            self.delete_blob(blob)
        return iter([])

    def _objects(self, name_starts_with: str | None) -> list[StoredObject]:
        try:
            return self._store.list(self.container_name, name_starts_with or "")
        except BucketNotFound:
            raise _container_not_found(self.container_name) from None

    def list_blobs(
        self, name_starts_with: str | None = None, include: Any = None, **kwargs: Any
    ) -> Iterator[BlobProperties]:
        objects = self._objects(name_starts_with)
        return iter([BlobProperties(self.container_name, o) for o in objects])

    def list_blob_names(self, **kwargs: Any) -> Iterator[str]:
        return iter([o.key for o in self._objects(kwargs.get("name_starts_with"))])

    def walk_blobs(
        self,
        name_starts_with: str | None = None,
        include: Any = None,
        delimiter: str = "/",
        **kwargs: Any,
    ) -> Iterator[BlobProperties | BlobPrefix]:
        prefix = name_starts_with or ""
        items: list[BlobProperties | BlobPrefix] = []
        seen: set[str] = set()
        for obj in self._objects(prefix):
            idx = obj.key.find(delimiter, len(prefix))
            if idx < 0:
                items.append(BlobProperties(self.container_name, obj))
                continue
            common = obj.key[: idx + len(delimiter)]
            if common not in seen:
                seen.add(common)
                items.append(BlobPrefix(self.container_name, common))
        return iter(items)

    def close(self) -> None:
        pass

    def __enter__(self) -> FakeContainerClient:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class FakeBlobClient(_Bound):
    """Stand-in for ``azure.storage.blob.BlobClient``."""

    def __init__(
        self,
        account_url: str,
        container_name: str,
        blob_name: str,
        snapshot: Any = None,
        credential: Any = None,
        *,
        _store: ObjectStore | None = None,
        **kwargs: Any,
    ) -> None:
        self._init_store(_store)
        self.account_url, _ = _split_url(account_url)
        self.container_name = container_name
        self.blob_name = blob_name
        self.snapshot = snapshot
        self.credential = credential
        self.url = f"{self.account_url}/{container_name}/{blob_name}"

    @classmethod
    def from_connection_string(
        cls,
        conn_str: str,
        container_name: str,
        blob_name: str,
        snapshot: Any = None,
        credential: Any = None,
        **kwargs: Any,
    ) -> FakeBlobClient:
        url, _ = _account_from_conn_str(conn_str)
        return cls(url, container_name, blob_name, snapshot, credential, **kwargs)

    @classmethod
    def from_blob_url(
        cls, blob_url: str, credential: Any = None, snapshot: Any = None, **kwargs: Any
    ) -> FakeBlobClient:
        account_url, path = _split_url(blob_url.split("?")[0])
        if len(path) < 2:
            raise ValueError(f"Invalid blob URL: {blob_url}")
        return cls(
            account_url, path[0], "/".join(path[1:]), snapshot, credential, **kwargs
        )

    def _stored(self) -> StoredObject:
        if not self._store.has_bucket(self.container_name):
            raise _container_not_found(self.container_name)
        if not self._store.exists(self.container_name, self.blob_name):
            raise _blob_not_found(self.container_name, self.blob_name)
        return self._store.head(self.container_name, self.blob_name)

    def exists(self, **kwargs: Any) -> bool:
        return self._store.exists(self.container_name, self.blob_name)

    def get_blob_properties(self, **kwargs: Any) -> BlobProperties:
        return BlobProperties(self.container_name, self._stored())

    def upload_blob(
        self,
        data: Any,
        blob_type: Any = "BlockBlob",
        length: int | None = None,
        metadata: dict[str, str] | None = None,
        *,
        overwrite: bool = False,
        content_settings: Any = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not self._store.has_bucket(self.container_name):
            raise _container_not_found(self.container_name)
        if not overwrite and self.exists():
            raise _error(
                ResourceExistsError,
                "BlobAlreadyExists",
                409,
                "The specified blob already exists.",
            )
        payload = to_bytes(data)
        if length is not None:
            payload = payload[:length]
        obj = self._store.put(
            self.container_name,
            self.blob_name,
            payload,
            content_type=getattr(content_settings, "content_type", None),
            metadata=metadata,
            create_bucket=False,
        )
        return {"etag": f'"{obj.etag}"', "last_modified": obj.last_modified}

    def download_blob(
        self,
        offset: int | None = None,
        length: int | None = None,
        *,
        encoding: str | None = None,
        **kwargs: Any,
    ) -> StorageStreamDownloader:
        obj = self._stored()
        data = obj.data
        if offset is not None:
            data = data[offset : None if length is None else offset + length]
        elif length is not None:
            raise ValueError("Offset value must not be None if length is set.")
        return StorageStreamDownloader(
            BlobProperties(self.container_name, obj), data, encoding
        )

    def delete_blob(self, delete_snapshots: Any = None, **kwargs: Any) -> None:
        self._stored()
        self._store.delete(self.container_name, self.blob_name)

    def set_blob_metadata(
        self, metadata: dict[str, str] | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        self._stored()
        obj = self._store.replace_metadata(
            self.container_name, self.blob_name, metadata=metadata or {}
        )
        return {"etag": f'"{obj.etag}"', "last_modified": obj.last_modified}

    def set_http_headers(
        self, content_settings: Any = None, **kwargs: Any
    ) -> dict[str, Any]:
        self._stored()
        obj = self._store.replace_metadata(
            self.container_name,
            self.blob_name,
            content_type=getattr(content_settings, "content_type", None),
        )
        return {"etag": f'"{obj.etag}"', "last_modified": obj.last_modified}

    def start_copy_from_url(self, source_url: str, **kwargs: Any) -> dict[str, Any]:
        source = FakeBlobClient.from_blob_url(source_url, _store=self._store)
        obj = source._stored()
        if not self._store.has_bucket(self.container_name):
            raise _container_not_found(self.container_name)
        copied = self._store.put(
            self.container_name,
            self.blob_name,
            obj.data,
            content_type=obj.content_type,
            metadata=kwargs.get("metadata") or obj.metadata,
            create_bucket=False,
        )
        return {
            "copy_id": copied.etag,
            "copy_status": "success",
            "etag": f'"{copied.etag}"',
            "last_modified": copied.last_modified,
        }

    def close(self) -> None:
        pass

    def __enter__(self) -> FakeBlobClient:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class FakeAzureBlob(FakeCloud):
    """In-memory Azure Blob Storage; patches ``azure.storage.blob`` while active."""

    provider = "azure"

    def service_client(
        self, account_url: str = f"https://{DEFAULT_ACCOUNT}.blob.core.windows.net"
    ) -> FakeBlobServiceClient:
        """A service client bound to this fake (works without the SDK installed)."""
        return FakeBlobServiceClient(account_url, _store=self.store)

    client = service_client

    def container_client(self, container: str) -> FakeContainerClient:
        return self.service_client().get_container_client(container)

    @property
    def connection_string(self) -> str:
        """A syntactically valid connection string for code that requires one."""
        return (
            f"DefaultEndpointsProtocol=https;AccountName={DEFAULT_ACCOUNT};"
            "AccountKey=ZmluZ2VzdA==;EndpointSuffix=core.windows.net"
        )

    def _constructors(self) -> list[tuple[str, Callable[..., Any]]]:
        store = self.store
        return [
            (
                f"azure.storage.blob:{name}",
                type(name, (base,), {"_default_store": store}),
            )
            for name, base in (
                ("BlobServiceClient", FakeBlobServiceClient),
                ("ContainerClient", FakeContainerClient),
                ("BlobClient", FakeBlobClient),
            )
        ]


__all__ = [
    "BlobPrefix",
    "BlobProperties",
    "ContainerProperties",
    "FakeAzureBlob",
    "FakeBlobClient",
    "FakeBlobServiceClient",
    "FakeContainerClient",
    "StorageStreamDownloader",
]
