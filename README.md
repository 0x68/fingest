# Pytest Fingest Fixture Plugin

This Pytest plugin allows you to easily define data-driven fixtures based on external files. It supports `JSON`, `CSV`, and `XML` data sources, and can automatically instantiate Python classes or functions using this data.

## Features

- Automatic registration of data-backed fixtures
- Supports JSON, CSV, and XML file formats
- Optional descriptions for improved debugging
- Configurable base data path via `pytest.ini`

---

## Installation

Place the plugin code inside your project (e.g. in `conftest.py`) or install it as a standalone plugin.

---

## Configuration

Add the following to your `pytest.ini`:

```ini
[pytest]
fingest_fixture_path = data  # Base directory for fixture data files

```

## Example Conftest

```python
from fingest.plugin import data_fixture
from fingest.types import BaseFixture, JSONFixture


@data_fixture("test.json", description="JSON File Foo Bar")
class JsonData(JSONFixture): ...


@data_fixture("test.xml", description="XML File Foo Bar")
class XMLData(BaseFixture): ...


@data_fixture("test.csv", description="CSV File FOO Bar")
class CSV(BaseFixture):
    """CSV File"""

    ...


@data_fixture("test.json", description="Func Bases")
def json_test_file(data):
    """Json File in func"""
    return data
```

## Example Test

```python

def test_data_fixture(JsonData):
    assert JsonData.data.get("Foo") == "Bar"


def test_data_fixtute(JsonData):
    assert JsonData.length() == 1


def test_xml(XMLData):
    assert XMLData


def test_csv(CSV):
    assert len(CSV.data) == 5


def test_json_func(json_test_file):
    assert json_test_file.get("Foo") == "Bar"

```
