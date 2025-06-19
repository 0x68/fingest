import pytest
import json
import csv
from lxml import etree
from pathlib import Path

_fixture_registry = {}


def pytest_addoption(parser):
    parser.addini(
        name="fingest_fixture_path",
        help="Base path for fixture data files",
        default="data",
    )


def pytest_configure(config):
    data_path = config.getini("fingest_fixture_path")
    config.fingest_fixture_path = data_path


def data_fixture(file_path: str, description: str = ""):
    """
    Decorator: register class as a data-backed fixture with optional
    Description.
    """

    def wrapper(obj):
        _fixture_registry[obj.__name__] = {
            "obj": obj,
            "path": Path(file_path),
            "description": description,
            "is_class": isinstance(obj, type),
        }
        return obj

    return wrapper


def _load_data(path: Path):
    """Loads data from file.

    params:
    path: Path to the data file.
    raises: ValueError in case of invalid path file extension.
    returns:
    """
    if path.suffix[1:].lower() == "json":
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    if path.suffix[1:].lower() == "csv":
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    if path.suffix[1:].lower() == "xml":
        return etree.parse(path)
    else:
        raise ValueError(f"Unsupported format: {path.suffix[1:].lower()}")


class FixtureWrapper:
    def __init__(self, instance, description: str):
        self._instance = instance
        self._description = description

    def __getattr__(self, item):
        return getattr(self._instance, item)

    def __repr__(self):
        return f"{self._description}"

    def __str__(self):
        return f"{self._instance}  (Fixture description: {self._description})"


def pytest_sessionstart(session):
    """
    Generate real fixtures at test session start.
    """
    data_root = getattr(session.config, "fingest_fixture_path", "data")
    for name, info in _fixture_registry.items():
        obj = info["obj"]
        path = Path(data_root) / Path(info["path"])
        desc = info["description"]
        is_class = info["is_class"]

        @pytest.fixture(name=name)
        def _fixture(obj=obj, path=path, desc=desc, is_class=is_class):
            data = _load_data(path)
            result = obj(data) if is_class else obj(data)
            return FixtureWrapper(result, desc)

        globals()[name] = _fixture
