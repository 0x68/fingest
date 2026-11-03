import pytest
from lxml import etree

from fingest.loaders import ParserRegistry, parse


def test_json_handles_utf8_bom():
    assert parse(b"\xef\xbb\xbf" + b'{"a": 1}', "x.json") == {"a": 1}


def test_jsonl_skips_blank_lines():
    assert parse(b'{"a":1}\n\n{"a":2}\n', "x.ndjson") == [{"a": 1}, {"a": 2}]


def test_csv_and_tsv():
    assert parse(b'name,note\nA,"multi\nline"\n', "x.csv") == [
        {"name": "A", "note": "multi\nline"}
    ]
    assert parse(b"a\tb\n1\t2\n", "x.TSV") == [{"a": "1", "b": "2"}]


def test_xml_returns_element_tree():
    tree = parse(b"<root><a>1</a></root>", "x.xml")
    assert isinstance(tree, etree._ElementTree)
    assert tree.getroot().findtext("a") == "1"


def test_xml_does_not_expand_external_entities(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP-SECRET")
    payload = (
        f'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file://{secret}">]>'
        "<r>&x;</r>"
    ).encode()
    tree = parse(payload, "x.xml")
    assert "TOP-SECRET" not in etree.tostring(tree).decode()


def test_text():
    assert parse("héllo".encode(), "notes.txt") == "héllo"


def test_unknown_extension_raises():
    with pytest.raises(ValueError, match=r"no parser for 'data\.bin'"):
        parse(b"\x00", "data.bin")
    with pytest.raises(ValueError, match="<none>"):
        parse(b"", "Makefile")


def test_parse_errors_are_wrapped():
    with pytest.raises(ValueError, match=r"failed to parse 'x\.json'"):
        parse(b"{", "x.json")


def test_registry_is_case_insensitive_and_isolated():
    reg = ParserRegistry()
    reg.register(".YAML", lambda raw: "yaml!")
    assert reg.parse(b"", "a.yaml") == "yaml!"
    assert ParserRegistry().get("yaml") is None
    assert "yaml" in repr(reg)
