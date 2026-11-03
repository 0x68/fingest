"""Provider-agnostic in-memory object store used by all cloud fakes."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import threading
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fingest.loaders import parse

IGNORED_SEED_FILES = frozenset({".gitkeep", ".keep", ".DS_Store", "Thumbs.db"})


class StorageError(Exception):
    """Base class for errors raised by :class:`ObjectStore`."""


class BucketNotFound(StorageError, KeyError):
    def __init__(self, bucket: str) -> None:
        super().__init__(f"bucket {bucket!r} does not exist")
        self.bucket = bucket

    def __str__(self) -> str:
        return str(self.args[0])


class ObjectNotFound(StorageError, KeyError):
    def __init__(self, bucket: str, key: str) -> None:
        super().__init__(f"object {key!r} does not exist in bucket {bucket!r}")
        self.bucket = bucket
        self.key = key

    def __str__(self) -> str:
        return str(self.args[0])


class BucketAlreadyExists(StorageError):
    def __init__(self, bucket: str) -> None:
        super().__init__(f"bucket {bucket!r} already exists")
        self.bucket = bucket


class BucketNotEmpty(StorageError):
    def __init__(self, bucket: str) -> None:
        super().__init__(f"bucket {bucket!r} is not empty")
        self.bucket = bucket


def _now() -> datetime:
    return datetime.now(UTC)


def to_bytes(data: Any) -> bytes:
    """Coerce test-friendly payloads into bytes.

    ``str`` is UTF-8 encoded, ``dict``/``list`` are JSON encoded, file-like
    objects are read.
    """
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray | memoryview):
        return bytes(data)
    if isinstance(data, str):
        return data.encode("utf-8")
    if isinstance(data, dict | list):
        return json.dumps(data).encode("utf-8")
    if hasattr(data, "read"):
        return to_bytes(data.read())
    if isinstance(data, Iterator):
        return b"".join(to_bytes(chunk) for chunk in data)
    raise TypeError(f"cannot store object of type {type(data).__name__}")


@dataclass(frozen=True)
class StoredObject:
    """An immutable object version."""

    key: str
    data: bytes
    content_type: str = "application/octet-stream"
    metadata: Mapping[str, str] = field(default_factory=dict)
    last_modified: datetime = field(default_factory=_now)
    generation: int = 1
    etag: str = ""

    def __post_init__(self) -> None:
        if not self.etag:
            object.__setattr__(self, "etag", hashlib.md5(self.data).hexdigest())

    @property
    def size(self) -> int:
        return len(self.data)

    @property
    def md5_base64(self) -> str:
        return base64.b64encode(hashlib.md5(self.data).digest()).decode()


@dataclass
class Bucket:
    name: str
    created: datetime = field(default_factory=_now)
    metadata: dict[str, str] = field(default_factory=dict)
    objects: dict[str, StoredObject] = field(default_factory=dict)


class ObjectStore:
    """A thread-safe, in-memory set of buckets holding immutable objects.

    The same store backs every provider fake; "bucket" means an S3 bucket, a
    GCS bucket or an Azure container.
    """

    def __init__(self) -> None:
        self._buckets: dict[str, Bucket] = {}
        self._lock = threading.RLock()
        self._generation = 0

    # -- buckets ---------------------------------------------------------------

    def create_bucket(self, name: str, *, exist_ok: bool = False) -> Bucket:
        with self._lock:
            if name in self._buckets:
                if exist_ok:
                    return self._buckets[name]
                raise BucketAlreadyExists(name)
            bucket = self._buckets[name] = Bucket(name)
            return bucket

    def delete_bucket(self, name: str, *, force: bool = False) -> None:
        with self._lock:
            bucket = self.bucket(name)
            if bucket.objects and not force:
                raise BucketNotEmpty(name)
            del self._buckets[name]

    def bucket(self, name: str) -> Bucket:
        with self._lock:
            try:
                return self._buckets[name]
            except KeyError:
                raise BucketNotFound(name) from None

    def has_bucket(self, name: str) -> bool:
        return name in self._buckets

    def buckets(self) -> list[Bucket]:
        with self._lock:
            return sorted(self._buckets.values(), key=lambda b: b.name)

    # -- objects ---------------------------------------------------------------

    def put(
        self,
        bucket: str,
        key: str,
        data: Any,
        *,
        content_type: str | None = None,
        metadata: Mapping[str, str] | None = None,
        create_bucket: bool = True,
        etag: str = "",
    ) -> StoredObject:
        """Store an object, replacing any existing one.

        ``data`` may be bytes, str, a dict/list (stored as JSON) or a file-like.
        """
        payload = to_bytes(data)
        if content_type is None:
            guessed = mimetypes.guess_type(key)[0]
            if guessed is None and isinstance(data, dict | list):
                guessed = "application/json"
            content_type = guessed or "application/octet-stream"
        with self._lock:
            target = (
                self.create_bucket(bucket, exist_ok=True)
                if create_bucket
                else self.bucket(bucket)
            )
            self._generation += 1
            obj = StoredObject(
                key=key,
                data=payload,
                content_type=content_type,
                metadata=dict(metadata or {}),
                generation=self._generation,
                etag=etag,
            )
            target.objects[key] = obj
            return obj

    def replace_metadata(
        self,
        bucket: str,
        key: str,
        *,
        metadata: Mapping[str, str] | None = None,
        content_type: str | None = None,
    ) -> StoredObject:
        with self._lock:
            current = self.head(bucket, key)
            updated = replace(
                current,
                metadata=dict(current.metadata if metadata is None else metadata),
                content_type=content_type or current.content_type,
                last_modified=_now(),
            )
            self.bucket(bucket).objects[key] = updated
            return updated

    def head(self, bucket: str, key: str) -> StoredObject:
        with self._lock:
            obj = self.bucket(bucket).objects.get(key)
            if obj is None:
                raise ObjectNotFound(bucket, key)
            return obj

    def exists(self, bucket: str, key: str) -> bool:
        with self._lock:
            return bucket in self._buckets and key in self._buckets[bucket].objects

    def delete(self, bucket: str, key: str, *, missing_ok: bool = False) -> None:
        with self._lock:
            objects = self.bucket(bucket).objects
            if key not in objects:
                if missing_ok:
                    return
                raise ObjectNotFound(bucket, key)
            del objects[key]

    def list(self, bucket: str, prefix: str = "") -> list[StoredObject]:
        """Objects in ``bucket`` whose key starts with ``prefix``, sorted by key."""
        with self._lock:
            objects = self.bucket(bucket).objects
            return [objects[k] for k in sorted(objects) if k.startswith(prefix)]

    # -- convenience readers ---------------------------------------------------

    def get_bytes(self, bucket: str, key: str) -> bytes:
        return self.head(bucket, key).data

    def get_text(self, bucket: str, key: str, encoding: str = "utf-8") -> str:
        return self.get_bytes(bucket, key).decode(encoding)

    def get_json(self, bucket: str, key: str) -> Any:
        return json.loads(self.get_bytes(bucket, key))

    def get_parsed(self, bucket: str, key: str) -> Any:
        """Parse an object with the parser registered for its extension."""
        return parse(self.get_bytes(bucket, key), key)

    # -- seeding / snapshots ---------------------------------------------------

    def load_dir(self, root: str | Path, *, bucket: str | None = None) -> None:
        """Seed the store from a directory.

        Without ``bucket`` every sub-directory of ``root`` becomes a bucket and
        every file below it an object (``<root>/<bucket>/<key>``). With
        ``bucket``, ``root`` itself is loaded as that single bucket.
        """
        root = Path(root)
        if not root.is_dir():
            raise NotADirectoryError(f"fingest: seed directory {root} does not exist")
        if bucket is not None:
            self._load_bucket_dir(bucket, root)
            return
        for child in sorted(root.iterdir()):
            if child.is_dir():
                self._load_bucket_dir(child.name, child)

    def _load_bucket_dir(self, bucket: str, directory: Path) -> None:
        self.create_bucket(bucket, exist_ok=True)
        for file in sorted(directory.rglob("*")):
            if file.is_file() and file.name not in IGNORED_SEED_FILES:
                self.put(
                    bucket, file.relative_to(directory).as_posix(), file.read_bytes()
                )

    def copy(self) -> ObjectStore:
        """A cheap independent copy (objects are immutable and shared)."""
        clone = ObjectStore()
        with self._lock:
            clone._generation = self._generation
            for name, bucket in self._buckets.items():
                clone._buckets[name] = Bucket(
                    name=name,
                    created=bucket.created,
                    metadata=dict(bucket.metadata),
                    objects=dict(bucket.objects),
                )
        return clone

    def snapshot(self) -> dict[str, dict[str, bytes]]:
        """``{bucket: {key: bytes}}`` — handy for asserting on the whole state."""
        with self._lock:
            return {
                name: {key: obj.data for key, obj in sorted(b.objects.items())}
                for name, b in sorted(self._buckets.items())
            }

    def __repr__(self) -> str:
        counts = ", ".join(f"{b.name}={len(b.objects)}" for b in self.buckets())
        return f"ObjectStore({counts})"
