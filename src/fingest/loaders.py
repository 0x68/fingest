"""Parsers that turn raw file content into Python data, selected by extension."""

from __future__ import annotations

import csv
import io
import json
import logging
import tempfile
import warnings
from collections.abc import Callable
from pathlib import Path, PurePath
from typing import Any

from lxml import etree

logger = logging.getLogger(__name__)

Parser = Callable[[bytes], Any]
"""A parser receives the raw file content and returns the parsed data."""

# Hardened parser: no network access, no entity expansion (XXE-safe).
_XML_PARSER = etree.XMLParser(resolve_entities=False, no_network=True)


def _decode(raw: bytes) -> str:
    return raw.decode("utf-8-sig")


def parse_json(raw: bytes) -> Any:
    return json.loads(_decode(raw))


def parse_jsonl(raw: bytes) -> list[Any]:
    return [json.loads(line) for line in _decode(raw).splitlines() if line.strip()]


def parse_csv(raw: bytes, delimiter: str = ",") -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(_decode(raw)), delimiter=delimiter))


def parse_tsv(raw: bytes) -> list[dict[str, str]]:
    return parse_csv(raw, delimiter="\t")


def parse_xml(raw: bytes) -> etree._ElementTree:
    return etree.ElementTree(etree.fromstring(raw, parser=_XML_PARSER))


def parse_text(raw: bytes) -> str:
    return _decode(raw)


class ParserRegistry:
    """Maps file extensions (without dot, case-insensitive) to parsers."""

    def __init__(self) -> None:
        self._parsers: dict[str, Parser] = {}
        for exts, parser in (
            (("json",), parse_json),
            (("jsonl", "ndjson"), parse_jsonl),
            (("csv",), parse_csv),
            (("tsv",), parse_tsv),
            (("xml",), parse_xml),
            (("txt", "text", "md"), parse_text),
        ):
            for ext in exts:
                self.register(ext, parser)

    @staticmethod
    def _normalize(extension: str) -> str:
        return extension.lower().lstrip(".")

    def register(self, extension: str, parser: Parser) -> None:
        self._parsers[self._normalize(extension)] = parser
        logger.debug("fingest: registered parser for .%s", extension)

    def get(self, extension: str) -> Parser | None:
        return self._parsers.get(self._normalize(extension))

    def parse(self, raw: bytes, name: str | PurePath) -> Any:
        """Parse ``raw`` using the parser registered for ``name``'s extension."""
        suffix = PurePath(name).suffix
        parser = self.get(suffix)
        if parser is None:
            ext = suffix or "<none>"
            known = ", ".join(sorted(self._parsers))
            raise ValueError(
                f"fingest: no parser for {str(name)!r} (extension {ext!r}); "
                f"known: {known}. Register one with fingest.register_parser() "
                "or pass parser=... to the decorator"
            )
        try:
            return parser(raw)
        except Exception as exc:
            raise ValueError(f"fingest: failed to parse {str(name)!r}: {exc}") from exc

    def __repr__(self) -> str:
        return f"ParserRegistry({', '.join(sorted(self._parsers))})"


registry = ParserRegistry()


def register_parser(extension: str, parser: Parser) -> None:
    """Register a parser for a file extension, globally.

    Example::

        import yaml
        register_parser("yaml", yaml.safe_load)
    """
    registry.register(extension, parser)


def register_loader(extension: str, loader: Callable[[Path], Any]) -> None:
    """Deprecated 1.x API: register a ``Path``-based loader.

    Use :func:`register_parser` (``bytes -> Any``) instead.
    """
    warnings.warn(
        "fingest.register_loader() is deprecated; use register_parser(ext, parser) "
        "where parser receives the file content as bytes",
        DeprecationWarning,
        stacklevel=2,
    )
    suffix = "." + extension.lower().lstrip(".")

    def parser(raw: bytes) -> Any:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"data{suffix}"
            path.write_bytes(raw)
            return loader(path)

    registry.register(extension, parser)


def parse(raw: bytes, name: str | PurePath) -> Any:
    """Parse ``raw`` content according to the extension of ``name``."""
    return registry.parse(raw, name)
