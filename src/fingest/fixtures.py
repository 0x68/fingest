"""The ``@data_fixture`` decorator and the machinery that turns it into pytest fixtures.

Fixtures are registered in the module that defines them (usually a
``conftest.py``), so pytest discovers and scopes them like any hand-written
fixture: a fixture in ``tests/api/conftest.py`` is only visible below
``tests/api``.
"""

from __future__ import annotations

import inspect
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, TypeVar

import pytest

from fingest._config import FIXTURE_PATH_INI, fixture_root
from fingest.loaders import Parser, parse
from fingest.types import BaseFixture

Scope = Literal["function", "class", "module", "package", "session"]
T = TypeVar("T")

_ATTR_PREFIX = "_fingest_fixture_"


class Source(Protocol):
    """Where a fixture's raw bytes come from."""

    @property
    def name(self) -> str:
        """A name whose extension selects the parser (e.g. ``users.json``)."""
        ...

    def read(self, request: pytest.FixtureRequest) -> bytes: ...


@dataclass(frozen=True)
class FileSource:
    """A file relative to ``fingest_fixture_path``."""

    path: str

    @property
    def name(self) -> str:
        return self.path

    def read(self, request: pytest.FixtureRequest) -> bytes:
        root = fixture_root(request.config)
        full = root / self.path
        if not full.is_file():
            raise FileNotFoundError(
                f"fingest: data file {self.path!r} not found at {full} "
                f"({FIXTURE_PATH_INI} resolves to {root})"
            )
        return full.read_bytes()


def data_fixture(
    path: str | Path,
    *,
    description: str = "",
    parser: Parser | None = None,
    scope: Scope = "function",
    name: str | None = None,
) -> Callable[[T], T]:
    """Register a class or function as a fixture backed by a data file.

    Args:
        path: File path relative to ``fingest_fixture_path``.
        description: Human readable label, available as ``fixture.description``.
        parser: Custom ``bytes -> Any`` parser; defaults to one chosen by extension.
        scope: pytest fixture scope.
        name: Fixture name; defaults to the decorated object's ``__name__``.

    A **class** is instantiated as ``cls(data, description=...)``. A **function**
    receives the parsed data as its first argument; its remaining parameters are
    resolved as regular pytest fixtures. Generator functions may ``yield`` to add
    teardown. The decorated object itself is returned unchanged.

    Example::

        @data_fixture("users.json")
        class users(JSONFixture): ...

        @data_fixture("orders.csv")
        def open_orders(data, tmp_path):
            return [row for row in data if row["status"] == "open"]
    """

    def decorator(obj: T) -> T:
        return register(
            obj,
            FileSource(str(path)),
            description=description,
            parser=parser,
            scope=scope,
            name=name,
        )

    return decorator


def register(
    obj: T,
    source: Source,
    *,
    description: str = "",
    parser: Parser | None = None,
    scope: Scope = "function",
    name: str | None = None,
) -> T:
    """Build a pytest fixture for ``obj`` and attach it to ``obj``'s module."""
    fixture_name = name or getattr(obj, "__name__", None)
    if not fixture_name:
        raise TypeError(f"fingest: cannot derive a fixture name for {obj!r}")

    def load(request: pytest.FixtureRequest) -> Any:
        raw = source.read(request)
        return parser(raw) if parser is not None else parse(raw, source.name)

    if isinstance(obj, type):
        func = _class_fixture(obj, load, description)
    elif callable(obj):
        func = _function_fixture(obj, load)
    else:
        raise TypeError(f"fingest: expected a class or function, got {obj!r}")

    func.__name__ = fixture_name
    func.__qualname__ = fixture_name
    func.__doc__ = description or getattr(obj, "__doc__", None)
    func.__module__ = obj.__module__

    module = sys.modules.get(obj.__module__)
    if module is None:  # pragma: no cover - defensive
        raise RuntimeError(
            f"fingest: module {obj.__module__!r} of {fixture_name!r} is not imported"
        )
    setattr(
        module,
        _ATTR_PREFIX + fixture_name,
        pytest.fixture(name=fixture_name, scope=scope)(func),
    )
    return obj


def _class_fixture(
    cls: type, load: Callable[[pytest.FixtureRequest], Any], description: str
) -> Callable[..., Any]:
    takes_description = issubclass(cls, BaseFixture)

    def fixture(request: pytest.FixtureRequest) -> Any:
        data = load(request)
        if takes_description:
            return cls(data, description=description)
        return cls(data)

    return fixture


def _function_fixture(
    func: Callable[..., Any], load: Callable[[pytest.FixtureRequest], Any]
) -> Callable[..., Any]:
    if inspect.iscoroutinefunction(func) or inspect.isasyncgenfunction(func):
        raise TypeError(
            f"fingest: {func.__qualname__}() is async; data fixtures must be "
            "synchronous functions"
        )
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    if not params or params[0].kind not in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ):
        raise TypeError(
            f"fingest: {func.__qualname__}() must accept the loaded data as its "
            "first positional parameter"
        )

    positional_only = [
        p.name for p in params[1:] if p.kind is inspect.Parameter.POSITIONAL_ONLY
    ]
    if positional_only:
        raise TypeError(
            f"fingest: {func.__qualname__}() dependencies cannot be positional-only: "
            f"{', '.join(positional_only)}"
        )
    # Every remaining named parameter is a pytest dependency. *args/**kwargs are
    # dropped, parameters with defaults keep them (pytest does not inject those).
    deps = [
        p.replace(kind=inspect.Parameter.KEYWORD_ONLY)
        for p in params[1:]
        if p.kind
        in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    ]
    wants_request = any(p.name == "request" for p in deps)
    if not wants_request:
        deps.insert(0, inspect.Parameter("request", inspect.Parameter.KEYWORD_ONLY))

    def call(kwargs: dict[str, Any]) -> Any:
        request = kwargs["request"] if wants_request else kwargs.pop("request")
        return func(load(request), **kwargs)

    fixture: Callable[..., Any]
    if inspect.isgeneratorfunction(func):

        def fixture(**kwargs: Any) -> Iterator[Any]:
            yield from call(kwargs)

    else:

        def fixture(**kwargs: Any) -> Any:
            return call(kwargs)

    fixture.__signature__ = sig.replace(  # type: ignore[union-attr]
        parameters=deps, return_annotation=inspect.Signature.empty
    )
    return fixture
