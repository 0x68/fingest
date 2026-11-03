"""Google Cloud Storage simulation.

:class:`FakeGCS` redirects construction of ``google.cloud.storage.Client``,
``Bucket`` and ``Blob`` to in-memory look-alikes while it is active. This works
however the classes were imported, even with ``from google.cloud.storage import
Client`` at the top of a module before the fake started. The SDK's own
classmethods (``Blob.from_uri``, ...) build fakes too. ``fake_gcs.client()``
returns a bound client and works without the SDK installed.

Errors are raised as the real ``google.api_core.exceptions`` (``NotFound``,
``Conflict``, ``PreconditionFailed``) when ``google-api-core`` is installed.
"""

from __future__ import annotations

import io
import mimetypes
import re
from collections.abc import Callable, Iterable, Iterator
from datetime import datetime
from pathlib import Path
from typing import IO, Any, ClassVar

from fingest.cloud.base import FakeCloud
from fingest.cloud.store import (
    BucketAlreadyExists,
    BucketNotEmpty,
    ObjectStore,
    StoredObject,
    to_bytes,
)

try:  # pragma: no cover - depends on installed extras
    from google.api_core.exceptions import Conflict, NotFound, PreconditionFailed
except ImportError:  # pragma: no cover

    class _GoogleAPIError(Exception):
        code = 500

    class NotFound(_GoogleAPIError):  # type: ignore[no-redef]
        code = 404

    class Conflict(_GoogleAPIError):  # type: ignore[no-redef]
        code = 409

    class PreconditionFailed(_GoogleAPIError):  # type: ignore[no-redef]
        code = 412


def _parse_gs_uri(uri: str) -> tuple[str, str]:
    match = re.match(r"^gs://([^/]+)/?(.*)$", uri)
    if not match:
        raise ValueError(f"URI {uri!r} is not a gs:// URI")
    return match.group(1), match.group(2)


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    out = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


class FakeGCSClient:
    """Stand-in for ``google.cloud.storage.Client``."""

    _default_store: ClassVar[ObjectStore | None] = None

    def __init__(
        self,
        project: str | None = None,
        credentials: Any = None,
        *args: Any,
        _store: ObjectStore | None = None,
        **kwargs: Any,
    ) -> None:
        store = _store if _store is not None else type(self)._default_store
        if store is None:
            raise RuntimeError(
                "fingest FakeGCSClient is not bound to a store; use the fake_gcs "
                "fixture or FakeGCS().client()"
            )
        self._store = store
        self.project = project or "fingest-project"
        self._credentials = credentials

    @classmethod
    def create_anonymous_client(cls) -> FakeGCSClient:
        return cls(project="<none>")

    def _bucket_cls(self) -> type[FakeGCSBucket]:
        return FakeGCSBucket

    def _as_bucket(self, bucket_or_name: Any) -> FakeGCSBucket:
        if isinstance(bucket_or_name, FakeGCSBucket):
            return bucket_or_name
        name = getattr(bucket_or_name, "name", bucket_or_name)
        if isinstance(name, str) and name.startswith("gs://"):
            name = _parse_gs_uri(name)[0]
        return FakeGCSBucket(self, name)

    def bucket(
        self, bucket_name: str, user_project: str | None = None, **kwargs: Any
    ) -> FakeGCSBucket:
        return FakeGCSBucket(self, bucket_name, user_project=user_project)

    def get_bucket(
        self, bucket_or_name: Any, *args: Any, **kwargs: Any
    ) -> FakeGCSBucket:
        bucket = self._as_bucket(bucket_or_name)
        bucket.reload()
        return bucket

    def lookup_bucket(
        self, bucket_name: str, *args: Any, **kwargs: Any
    ) -> FakeGCSBucket | None:
        try:
            return self.get_bucket(bucket_name)
        except NotFound:
            return None

    def create_bucket(
        self,
        bucket_or_name: Any,
        *args: Any,
        location: str | None = None,
        **kwargs: Any,
    ) -> FakeGCSBucket:
        bucket = self._as_bucket(bucket_or_name)
        try:
            self._store.create_bucket(bucket.name)
        except BucketAlreadyExists:
            raise Conflict(
                f"POST https://storage.googleapis.com/storage/v1/b: "
                f"The bucket {bucket.name!r} already exists."
            ) from None
        bucket.location = location or "US"
        return bucket

    def list_buckets(
        self,
        max_results: int | None = None,
        *args: Any,
        prefix: str = "",
        **kwargs: Any,
    ) -> Iterator[FakeGCSBucket]:
        names = [b.name for b in self._store.buckets() if b.name.startswith(prefix)]
        return iter([FakeGCSBucket(self, n) for n in names[:max_results]])

    def list_blobs(
        self,
        bucket_or_name: Any,
        max_results: int | None = None,
        page_token: str | None = None,
        prefix: str | None = None,
        delimiter: str | None = None,
        start_offset: str | None = None,
        end_offset: str | None = None,
        include_trailing_delimiter: bool | None = None,
        *args: Any,
        match_glob: str | None = None,
        **kwargs: Any,
    ) -> FakeBlobIterator:
        bucket = self._as_bucket(bucket_or_name)
        prefix = prefix or ""
        try:
            objects = self._store.list(bucket.name, prefix)
        except KeyError:
            raise NotFound(
                f"GET https://storage.googleapis.com/storage/v1/b/{bucket.name}/o: "
                "The specified bucket does not exist."
            ) from None
        glob = _glob_to_regex(match_glob) if match_glob else None
        blobs: list[FakeGCSBlob] = []
        prefixes: set[str] = set()
        for obj in objects:
            if start_offset and obj.key < start_offset:
                continue
            if end_offset and obj.key >= end_offset:
                continue
            if glob and not glob.match(obj.key):
                continue
            if delimiter:
                idx = obj.key.find(delimiter, len(prefix))
                if idx >= 0:
                    common = obj.key[: idx + len(delimiter)]
                    prefixes.add(common)
                    if not (include_trailing_delimiter and obj.key == common):
                        continue
            blobs.append(FakeGCSBlob._from_stored(bucket, obj))
        if max_results is not None:
            blobs = blobs[:max_results]
        return FakeBlobIterator(self, blobs, prefixes, max_results)


class FakeBlobIterator:
    """Iterable result of ``list_blobs`` with ``.prefixes`` and ``.pages``."""

    def __init__(
        self,
        client: FakeGCSClient,
        blobs: list[FakeGCSBlob],
        prefixes: set[str],
        max_results: int | None,
    ) -> None:
        self.client = client
        self._blobs = blobs
        self.prefixes = prefixes
        self.max_results = max_results
        self.num_results = 0
        self.next_page_token: str | None = None

    def __iter__(self) -> Iterator[FakeGCSBlob]:
        for blob in self._blobs:
            self.num_results += 1
            yield blob

    @property
    def pages(self) -> Iterator[FakeBlobPage]:
        yield FakeBlobPage(self._blobs, self.prefixes)


class FakeBlobPage:
    def __init__(self, blobs: list[FakeGCSBlob], prefixes: set[str]) -> None:
        self._blobs = blobs
        self.prefixes = prefixes
        self.num_items = len(blobs)

    def __iter__(self) -> Iterator[FakeGCSBlob]:
        return iter(self._blobs)


class FakeGCSBucket:
    """Stand-in for ``google.cloud.storage.Bucket``."""

    _default_store: ClassVar[ObjectStore | None] = None

    def __init__(
        self,
        client: FakeGCSClient | None,
        name: str | None = None,
        user_project: str | None = None,
        generation: int | None = None,
    ) -> None:
        self.client = client
        self.name = name or ""
        self.user_project = user_project
        self.location: str | None = None
        self.time_created: datetime | None = None

    @classmethod
    def from_string(
        cls, uri: str, client: FakeGCSClient | None = None
    ) -> FakeGCSBucket:
        return cls(client, _parse_gs_uri(uri)[0])

    from_uri = from_string

    @property
    def _store(self) -> ObjectStore:
        if self.client is not None:
            return self.client._store
        if type(self)._default_store is not None:
            return type(self)._default_store  # type: ignore[return-value]
        raise RuntimeError("fingest FakeGCSBucket has no client")

    @property
    def path(self) -> str:
        return f"/b/{self.name}"

    def _not_found(self) -> NotFound:
        return NotFound(
            f"GET https://storage.googleapis.com/storage/v1/b/{self.name}: "
            "The specified bucket does not exist."
        )

    def exists(self, *args: Any, **kwargs: Any) -> bool:
        return self._store.has_bucket(self.name)

    def reload(self, *args: Any, **kwargs: Any) -> None:
        if not self._store.has_bucket(self.name):
            raise self._not_found()
        self.time_created = self._store.bucket(self.name).created
        self.location = self.location or "US"

    def create(
        self, client: FakeGCSClient | None = None, *args: Any, **kwargs: Any
    ) -> None:
        owner = client or self.client
        if owner is None:
            raise RuntimeError("fingest FakeGCSBucket.create() needs a client")
        owner.create_bucket(self, location=kwargs.get("location"))

    def delete(self, force: bool = False, *args: Any, **kwargs: Any) -> None:
        if not self.exists():
            raise self._not_found()
        try:
            self._store.delete_bucket(self.name, force=force)
        except BucketNotEmpty:
            raise Conflict(
                f"DELETE https://storage.googleapis.com/storage/v1/b/{self.name}: "
                "The bucket you tried to delete is not empty."
            ) from None

    def blob(self, blob_name: str, *args: Any, **kwargs: Any) -> FakeGCSBlob:
        return FakeGCSBlob(blob_name, self)

    def get_blob(self, blob_name: str, *args: Any, **kwargs: Any) -> FakeGCSBlob | None:
        blob = FakeGCSBlob(blob_name, self)
        try:
            blob.reload()
        except NotFound:
            return None
        return blob

    def list_blobs(self, *args: Any, **kwargs: Any) -> FakeBlobIterator:
        if self.client is None:
            raise RuntimeError("fingest FakeGCSBucket.list_blobs() needs a client")
        return self.client.list_blobs(self, *args, **kwargs)

    def delete_blob(self, blob_name: str, *args: Any, **kwargs: Any) -> None:
        FakeGCSBlob(blob_name, self).delete(**kwargs)

    def delete_blobs(
        self, blobs: Iterable[Any], on_error: Any = None, *args: Any, **kwargs: Any
    ) -> None:
        for blob in blobs:
            name = getattr(blob, "name", blob)
            try:
                self.delete_blob(name)
            except NotFound:
                if on_error is None:
                    raise
                on_error(blob)

    def copy_blob(
        self,
        blob: FakeGCSBlob,
        destination_bucket: FakeGCSBucket,
        new_name: str | None = None,
        *args: Any,
        if_generation_match: int | None = None,
        **kwargs: Any,
    ) -> FakeGCSBlob:
        source = blob._stored()
        target = FakeGCSBlob(new_name or blob.name, destination_bucket)
        target._check_generation(if_generation_match)
        if not destination_bucket.exists():
            raise destination_bucket._not_found()
        stored = destination_bucket._store.put(
            destination_bucket.name,
            target.name,
            source.data,
            content_type=source.content_type,
            metadata=source.metadata,
            create_bucket=False,
        )
        target._apply(stored)
        return target

    def rename_blob(
        self, blob: FakeGCSBlob, new_name: str, *args: Any, **kwargs: Any
    ) -> FakeGCSBlob:
        renamed = self.copy_blob(blob, self, new_name)
        if blob.name != new_name:
            blob.delete()
        return renamed

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FakeGCSBucket) and other.name == self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __repr__(self) -> str:
        return f"<Bucket: {self.name}>"


class FakeGCSBlob:
    """Stand-in for ``google.cloud.storage.Blob``.

    Like the real SDK, server-side properties (``size``, ``updated``, ...) are
    ``None`` until the blob was fetched via ``reload()``, ``get_blob()``,
    ``list_blobs()``, a download or an upload.
    """

    def __init__(
        self,
        name: str,
        bucket: FakeGCSBucket,
        chunk_size: int | None = None,
        encryption_key: bytes | None = None,
        kms_key_name: str | None = None,
        generation: int | None = None,
    ) -> None:
        self.name = name
        self.bucket = bucket
        self.chunk_size = chunk_size
        self.content_type: str | None = None
        self.metadata: dict[str, str] | None = None
        self.cache_control: str | None = None
        self.content_encoding: str | None = None
        self.content_disposition: str | None = None
        self.content_language: str | None = None
        self.size: int | None = None
        self.md5_hash: str | None = None
        self.crc32c: str | None = None
        self.etag: str | None = None
        self.generation: int | None = generation
        self.metageneration: int | None = None
        self.updated: datetime | None = None
        self.time_created: datetime | None = None
        self.storage_class: str | None = None

    @classmethod
    def from_string(cls, uri: str, client: FakeGCSClient | None = None) -> FakeGCSBlob:
        bucket_name, name = _parse_gs_uri(uri)
        return cls(name, FakeGCSBucket(client, bucket_name))

    from_uri = from_string

    @classmethod
    def _from_stored(cls, bucket: FakeGCSBucket, obj: StoredObject) -> FakeGCSBlob:
        blob = cls(obj.key, bucket)
        blob._apply(obj)
        return blob

    # -- helpers ---------------------------------------------------------------

    @property
    def client(self) -> FakeGCSClient | None:
        return self.bucket.client

    @property
    def _store(self) -> ObjectStore:
        return self.bucket._store

    @property
    def path(self) -> str:
        return f"{self.bucket.path}/o/{self.name}"

    @property
    def public_url(self) -> str:
        return f"https://storage.googleapis.com/{self.bucket.name}/{self.name}"

    @property
    def id(self) -> str | None:
        if self.generation is None:
            return None
        return f"{self.bucket.name}/{self.name}/{self.generation}"

    def _not_found(self) -> NotFound:
        return NotFound(
            f"GET https://storage.googleapis.com/storage/v1/b/{self.bucket.name}"
            f"/o/{self.name}: No such object: {self.bucket.name}/{self.name}"
        )

    def _stored(self) -> StoredObject:
        if not self._store.exists(self.bucket.name, self.name):
            raise self._not_found()
        return self._store.head(self.bucket.name, self.name)

    def _apply(self, obj: StoredObject) -> None:
        self.size = obj.size
        self.content_type = obj.content_type
        self.metadata = dict(obj.metadata) or None
        self.md5_hash = obj.md5_base64
        self.etag = obj.etag
        self.generation = obj.generation
        self.metageneration = 1
        self.updated = obj.last_modified
        self.time_created = obj.last_modified
        self.storage_class = "STANDARD"

    def _check_generation(
        self,
        if_generation_match: int | None,
        if_generation_not_match: int | None = None,
    ) -> None:
        if if_generation_match is None and if_generation_not_match is None:
            return
        exists = self._store.exists(self.bucket.name, self.name)
        current = (
            self._store.head(self.bucket.name, self.name).generation if exists else 0
        )
        if (if_generation_match is not None and current != if_generation_match) or (
            if_generation_not_match is not None and current == if_generation_not_match
        ):
            raise PreconditionFailed(
                f"{self.bucket.name}/{self.name}: At least one of the pre-conditions "
                "you specified did not hold."
            )

    # -- metadata --------------------------------------------------------------

    def exists(self, *args: Any, **kwargs: Any) -> bool:
        return self._store.exists(self.bucket.name, self.name)

    def reload(self, *args: Any, **kwargs: Any) -> None:
        self._apply(self._stored())

    def patch(self, *args: Any, **kwargs: Any) -> None:
        self._stored()
        stored = self._store.replace_metadata(
            self.bucket.name,
            self.name,
            metadata=self.metadata or {},
            content_type=self.content_type,
        )
        self._apply(stored)

    update = patch

    def delete(
        self,
        *args: Any,
        if_generation_match: int | None = None,
        if_generation_not_match: int | None = None,
        **kwargs: Any,
    ) -> None:
        self._stored()
        self._check_generation(if_generation_match, if_generation_not_match)
        self._store.delete(self.bucket.name, self.name)

    # -- downloads -------------------------------------------------------------

    def download_as_bytes(
        self,
        client: Any = None,
        start: int | None = None,
        end: int | None = None,
        *args: Any,
        if_generation_match: int | None = None,
        if_generation_not_match: int | None = None,
        **kwargs: Any,
    ) -> bytes:
        obj = self._stored()
        self._check_generation(if_generation_match, if_generation_not_match)
        self._apply(obj)
        data = obj.data
        if start is not None or end is not None:
            data = data[start or 0 : None if end is None else end + 1]
        return data

    def download_as_string(self, *args: Any, **kwargs: Any) -> bytes:
        return self.download_as_bytes(*args, **kwargs)

    def download_as_text(
        self,
        client: Any = None,
        start: int | None = None,
        end: int | None = None,
        raw_download: bool = False,
        encoding: str | None = None,
        **kwargs: Any,
    ) -> str:
        data = self.download_as_bytes(client, start, end, **kwargs)
        return data.decode(encoding or "utf-8")

    def download_to_file(self, file_obj: IO[bytes], *args: Any, **kwargs: Any) -> None:
        file_obj.write(self.download_as_bytes(**kwargs))

    def download_to_filename(
        self, filename: str | Path, *args: Any, **kwargs: Any
    ) -> None:
        data = self.download_as_bytes(**kwargs)
        Path(filename).write_bytes(data)

    # -- uploads ---------------------------------------------------------------

    def _upload(
        self,
        data: bytes,
        content_type: str | None,
        if_generation_match: int | None,
        if_generation_not_match: int | None,
    ) -> None:
        if not self.bucket.exists():
            raise self.bucket._not_found()
        self._check_generation(if_generation_match, if_generation_not_match)
        stored = self._store.put(
            self.bucket.name,
            self.name,
            data,
            content_type=content_type,
            metadata=self.metadata or {},
            create_bucket=False,
        )
        self._apply(stored)

    def upload_from_string(
        self,
        data: str | bytes,
        content_type: str = "text/plain",
        client: Any = None,
        predefined_acl: Any = None,
        if_generation_match: int | None = None,
        if_generation_not_match: int | None = None,
        **kwargs: Any,
    ) -> None:
        self._upload(
            to_bytes(data),
            self.content_type or content_type,
            if_generation_match,
            if_generation_not_match,
        )

    def upload_from_file(
        self,
        file_obj: IO[Any],
        rewind: bool = False,
        size: int | None = None,
        content_type: str | None = None,
        *args: Any,
        if_generation_match: int | None = None,
        if_generation_not_match: int | None = None,
        **kwargs: Any,
    ) -> None:
        if rewind:
            file_obj.seek(0)
        data = to_bytes(file_obj.read() if size is None else file_obj.read(size))
        self._upload(
            data,
            content_type or self.content_type or "application/octet-stream",
            if_generation_match,
            if_generation_not_match,
        )

    def upload_from_filename(
        self,
        filename: str | Path,
        content_type: str | None = None,
        *args: Any,
        if_generation_match: int | None = None,
        if_generation_not_match: int | None = None,
        **kwargs: Any,
    ) -> None:
        guessed = mimetypes.guess_type(str(filename))[0]
        self._upload(
            Path(filename).read_bytes(),
            content_type or self.content_type or guessed or "application/octet-stream",
            if_generation_match,
            if_generation_not_match,
        )

    def open(
        self,
        mode: str = "r",
        chunk_size: int | None = None,
        ignore_flush: bool | None = None,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
        **kwargs: Any,
    ) -> IO[Any]:
        if mode in ("r", "rt", "rb"):
            raw = io.BytesIO(self.download_as_bytes())
            if mode == "rb":
                return raw
            return io.TextIOWrapper(
                raw, encoding=encoding or "utf-8", errors=errors, newline=newline
            )
        if mode in ("w", "wt", "wb"):
            writer = _UploadOnClose(self, kwargs.get("content_type"))
            if mode == "wb":
                return writer
            return io.TextIOWrapper(
                writer, encoding=encoding or "utf-8", errors=errors, newline=newline
            )
        raise ValueError(f"Unsupported mode {mode!r}")

    def __repr__(self) -> str:
        return f"<Blob: {self.bucket.name}, {self.name}, {self.generation}>"


class _UploadOnClose(io.BytesIO):
    def __init__(self, blob: FakeGCSBlob, content_type: str | None) -> None:
        super().__init__()
        self._blob = blob
        self._content_type = content_type

    def close(self) -> None:
        if not self.closed:
            self._blob._upload(
                self.getvalue(),
                self._content_type or self._blob.content_type or "text/plain",
                None,
                None,
            )
        super().close()


class FakeGCS(FakeCloud):
    """In-memory Google Cloud Storage; patches ``google.cloud.storage`` while active."""

    provider = "gcs"

    def client(self, project: str | None = None) -> FakeGCSClient:
        """A client bound to this fake (works without the SDK installed)."""
        return FakeGCSClient(project=project, _store=self.store)

    def _constructors(self) -> list[tuple[str, Callable[..., Any]]]:
        store = self.store
        bound = {
            name: type(name, (base,), {"_default_store": store})
            for name, base in (
                ("Client", FakeGCSClient),
                ("Bucket", FakeGCSBucket),
                ("Blob", FakeGCSBlob),
            )
        }
        return [(f"google.cloud.storage:{name}", cls) for name, cls in bound.items()]
