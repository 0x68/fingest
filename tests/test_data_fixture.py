"""Behaviour of @data_fixture: dependency injection, scoping, errors."""

import inspect

import pytest

from conftest import TEARDOWN_LOG, SessionUsers
from fingest import data_fixture, register_loader, register_parser
from fingest.loaders import registry


def test_class_fixture(JsonData):
    assert JsonData["Foo"] == "Bar"
    assert JsonData.description == "JSON File Foo Bar"


def test_function_fixture_with_dependencies(function_with_deps):
    assert function_with_deps["data"] == {"Foo": "Bar"}
    assert function_with_deps["another_dep"] == {"key": "value"}
    assert function_with_deps["combined"] == "dependency_value_Bar"


def test_optional_parameters_keep_defaults(function_with_optional_deps):
    assert function_with_optional_deps["optional"] == "default"
    assert function_with_optional_deps["mock_dep"] == "dependency_value"


def test_varargs_are_ignored(function_with_varargs):
    assert function_with_varargs["args"] == ()
    assert function_with_varargs["kwargs"] == {}


def test_function_can_request_request(function_with_request):
    assert function_with_request == "test_function_can_request_request"


def test_generator_fixture_runs_teardown(generator_fixture):
    assert generator_fixture == {"Foo": "Bar"}
    assert TEARDOWN_LOG[-1] == "setup"


def test_generator_fixture_teardown_happened():
    assert TEARDOWN_LOG[-1] == "teardown"


def test_session_scope_and_custom_name(session_users, request):
    request.getfixturevalue("session_users")
    assert isinstance(session_users, SessionUsers)
    assert SessionUsers.instances == 1


def test_decorator_returns_original_object():
    class Plain:
        pass

    def func(data):
        return data

    assert data_fixture("test.json")(Plain) is Plain
    assert data_fixture("test.json")(func) is func
    assert inspect.signature(func).parameters.keys() == {"data"}


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("def f(): pass", "first positional parameter"),
        ("def f(*, data): pass", "first positional parameter"),
        ("def f(data, dep, /): pass", "positional-only"),
        ("async def f(data): pass", "async"),
    ],
)
def test_invalid_function_signatures_fail_at_definition(source, message):
    namespace: dict = {}
    exec(source, namespace)
    namespace["f"].__module__ = __name__
    with pytest.raises(TypeError, match=message):
        data_fixture("test.json")(namespace["f"])


def test_register_parser_and_custom_parser_argument(pytester):
    pytester.makeini("[pytest]\nfingest_fixture_path = data\n")
    pytester.mkdir("data")
    pytester.path.joinpath("data", "pairs.kv").write_text("a=1\nb=2\n")
    pytester.makeconftest(
        """
        from fingest import data_fixture, register_parser

        def kv(raw):
            return dict(line.split("=") for line in raw.decode().splitlines())

        register_parser("kv", kv)

        @data_fixture("pairs.kv")
        def pairs(data):
            return data

        @data_fixture("pairs.kv", parser=lambda raw: raw.upper())
        def shouting(data):
            return data
        """
    )
    pytester.makepyfile(
        """
        def test_it(pairs, shouting):
            assert pairs == {"a": "1", "b": "2"}
            assert shouting == b"A=1\\nB=2\\n"
        """
    )
    pytester.runpytest("-p", "no:cacheprovider").assert_outcomes(passed=1)


def test_register_loader_is_deprecated_but_works(tmp_path):
    with pytest.warns(DeprecationWarning, match="register_parser"):
        register_loader("legacy", lambda path: path.read_text().strip())
    try:
        assert registry.parse(b" hi ", "x.legacy") == "hi"
    finally:
        registry._parsers.pop("legacy")
    register_parser("tmpfmt", bytes.upper)
    try:
        assert registry.parse(b"x", "a.TMPFMT") == b"X"
    finally:
        registry._parsers.pop("tmpfmt")


def test_fixture_is_scoped_to_its_conftest_directory(pytester):
    """Fixtures defined in nested conftests are only visible below them."""
    pytester.makeini("[pytest]\nfingest_fixture_path = data\n")
    pytester.mkdir("data")
    pytester.path.joinpath("data", "a.json").write_text('{"v": 1}')
    sub = pytester.mkpydir("sub")
    sub.joinpath("conftest.py").write_text(
        "from fingest import data_fixture, JSONFixture\n"
        "@data_fixture('a.json')\n"
        "class nested(JSONFixture): ...\n"
    )
    sub.joinpath("test_sub.py").write_text(
        "def test_sub(nested):\n    assert nested['v'] == 1\n"
    )
    pytester.makepyfile(test_top="def test_top(nested):\n    pass\n")
    result = pytester.runpytest("-p", "no:cacheprovider")
    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*fixture 'nested' not found*"])


def test_fixture_path_is_relative_to_rootdir_not_cwd(pytester, monkeypatch):
    pytester.makeini("[pytest]\nfingest_fixture_path = data\n")
    pytester.mkdir("data")
    pytester.path.joinpath("data", "a.json").write_text('{"v": 1}')
    pytester.makeconftest(
        "from fingest import data_fixture\n"
        "@data_fixture('a.json')\n"
        "def a(data):\n    return data\n"
    )
    pytester.makepyfile("def test_a(a):\n    assert a == {'v': 1}\n")
    elsewhere = pytester.mkdir("elsewhere")
    monkeypatch.chdir(elsewhere)
    result = pytester.runpytest(
        "-p", "no:cacheprovider", f"--rootdir={pytester.path}", str(pytester.path)
    )
    result.assert_outcomes(passed=1)


def test_missing_file_and_unknown_extension_errors(pytester):
    pytester.makeini("[pytest]\nfingest_fixture_path = data\n")
    pytester.mkdir("data")
    pytester.path.joinpath("data", "users.jsn").write_text("{}")
    pytester.makeconftest(
        "from fingest import data_fixture\n"
        "@data_fixture('missing.json')\n"
        "def missing(data): ...\n"
        "@data_fixture('users.jsn')\n"
        "def typo(data): ...\n"
    )
    pytester.makepyfile("def test_missing(missing): pass\ndef test_typo(typo): pass\n")
    result = pytester.runpytest("-p", "no:cacheprovider")
    result.assert_outcomes(errors=2)
    result.stdout.fnmatch_lines(
        [
            "*FileNotFoundError: fingest: data file 'missing.json' not found*",
            "*ValueError: fingest: no parser for 'users.jsn'*",
        ]
    )


def test_invalid_json_reports_file(pytester):
    pytester.makeini("[pytest]\nfingest_fixture_path = data\n")
    pytester.mkdir("data")
    pytester.path.joinpath("data", "bad.json").write_text("{nope")
    pytester.makeconftest(
        "from fingest import data_fixture, JSONFixture\n"
        "@data_fixture('bad.json')\n"
        "class bad(JSONFixture): ...\n"
    )
    pytester.makepyfile("def test_bad(bad): pass\n")
    result = pytester.runpytest("-p", "no:cacheprovider")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*failed to parse 'bad.json'*"])
