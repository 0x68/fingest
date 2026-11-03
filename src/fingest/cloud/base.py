"""Shared behaviour of the provider fakes: store delegation and SDK patching."""

from __future__ import annotations

import importlib
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from types import TracebackType
from typing import Any, ClassVar, Self

from fingest.cloud.store import ObjectStore, StoredObject


def _resolve(path: str) -> Any:
    """Import ``module[:Class.attr]``; ``None`` if the SDK is not installed."""
    module_name, _, qualname = path.partition(":")
    try:
        target: Any = importlib.import_module(module_name)
        for part in filter(None, qualname.split(".")):
            target = getattr(target, part)
    except (ImportError, AttributeError):
        return None
    return target


# Constructor redirection. After ``del cls.__new__`` CPython keeps rejecting
# constructor arguments ("object.__new__() takes exactly one argument"), so
# each SDK class gets one permanent dispatcher instead. It is inert unless a
# fake is active and only affects the exact class (never subclasses). This
# catches ``from sdk import Client`` imports done before the fake started.
_redirects: dict[type, list[Callable[..., Any]]] = {}
_redirect_lock = threading.Lock()

# At most one active fake per provider: overlapping patches would restore the
# wrong originals and make it ambiguous which store a client talks to.
_active_by_provider: dict[str, FakeCloud] = {}


def _install_dispatcher(cls: type) -> None:
    if cls in _redirects:
        return
    original_new: Any = cls.__new__

    def __new__(klass: type, *args: Any, **kwargs: Any) -> Any:
        factories = _redirects.get(klass) if klass is cls else None
        if factories:
            return factories[-1](*args, **kwargs)
        if original_new is object.__new__:
            return object.__new__(klass)
        return original_new(klass, *args, **kwargs)

    setattr(cls, "__new__", __new__)  # noqa: B010 - keep mypy out of it
    _redirects[cls] = []


class FakeCloud:
    """Base class of :class:`FakeS3`, :class:`FakeGCS` and :class:`FakeAzureBlob`.

    Wraps an :class:`ObjectStore` with helpers for arranging and asserting test
    state, and intercepts the provider SDK while active (``start``/``stop`` or as
    a context manager). In tests use the ``fake_s3``/``fake_gcs``/
    ``fake_azure_blob`` fixtures, which handle activation and seeding for you.
    """

    provider: ClassVar[str]

    def __init__(self, store: ObjectStore | None = None) -> None:
        self.store = store if store is not None else ObjectStore()
        self._undo: list[tuple[Any, str, Any]] = []
        self._installed: list[tuple[type, Callable[..., Any]]] = []
        self._active = False

    # -- lifecycle -------------------------------------------------------------

    def start(self) -> Self:
        with _redirect_lock:
            current = _active_by_provider.get(self.provider)
            if current is not None:
                raise RuntimeError(
                    f"{type(self).__name__}: another fake for {self.provider!r} is "
                    f"already active ({current!r}); stop it first"
                )
            _active_by_provider[self.provider] = self
        for path, attr, replacement in self._patches():
            target = _resolve(path)
            if target is None or not hasattr(target, attr):
                continue  # SDK (or this part of it) not installed
            self._undo.append((target, attr, getattr(target, attr)))
            setattr(target, attr, replacement)
        for path, factory in self._constructors():
            cls = _resolve(path)
            if not isinstance(cls, type):
                continue
            with _redirect_lock:
                _install_dispatcher(cls)
                _redirects[cls].append(factory)
            self._installed.append((cls, factory))
        self._active = True
        return self

    def stop(self) -> None:
        while self._undo:
            target, attr, original = self._undo.pop()
            setattr(target, attr, original)
        with _redirect_lock:
            while self._installed:
                cls, factory = self._installed.pop()
                _redirects[cls].remove(factory)
            if _active_by_provider.get(self.provider) is self:
                del _active_by_provider[self.provider]
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def __enter__(self) -> Self:
        return self.start()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.stop()

    def _patches(self) -> list[tuple[str, str, Any]]:
        """``(target, attribute, replacement)`` triples to install while active.

        ``target`` is a module path, optionally followed by ``:Class`` to patch
        a class attribute. Targets that cannot be imported are skipped.
        """
        return []

    def _constructors(self) -> list[tuple[str, Callable[..., Any]]]:
        """``("module:Class", factory)`` pairs: instantiating the SDK class
        returns ``factory(*args, **kwargs)`` instead while active."""
        return []

    # -- arrange / assert helpers ---------------------------------------------

    def create_bucket(self, name: str, *, exist_ok: bool = True) -> None:
        self.store.create_bucket(name, exist_ok=exist_ok)

    def put(
        self,
        bucket: str,
        key: str,
        data: Any,
        *,
        content_type: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> StoredObject:
        """Store an object (creating the bucket if needed)."""
        return self.store.put(
            bucket, key, data, content_type=content_type, metadata=metadata
        )

    def get(self, bucket: str, key: str) -> StoredObject:
        return self.store.head(bucket, key)

    def get_bytes(self, bucket: str, key: str) -> bytes:
        return self.store.get_bytes(bucket, key)

    def get_text(self, bucket: str, key: str, encoding: str = "utf-8") -> str:
        return self.store.get_text(bucket, key, encoding)

    def get_json(self, bucket: str, key: str) -> Any:
        return self.store.get_json(bucket, key)

    def get_parsed(self, bucket: str, key: str) -> Any:
        return self.store.get_parsed(bucket, key)

    def exists(self, bucket: str, key: str) -> bool:
        return self.store.exists(bucket, key)

    def delete(self, bucket: str, key: str) -> None:
        self.store.delete(bucket, key, missing_ok=True)

    def keys(self, bucket: str, prefix: str = "") -> list[str]:
        return [obj.key for obj in self.store.list(bucket, prefix)]

    def buckets(self) -> list[str]:
        return [b.name for b in self.store.buckets()]

    def load_dir(self, root: str | Path, *, bucket: str | None = None) -> None:
        self.store.load_dir(root, bucket=bucket)

    def snapshot(self) -> dict[str, dict[str, bytes]]:
        return self.store.snapshot()

    def __repr__(self) -> str:
        state = "active" if self.active else "inactive"
        return f"{type(self).__name__}({state}, {self.store!r})"
