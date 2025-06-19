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

## Example JSON

```python

from plugin import data_fixture

@data_fixture("users.json", description="Example user list")
class UserData:
    def __init__(self, data):
        self.users = data



def test_user_count(UserData):
    assert len(UserData.users) > 0

```

## Example CSV

```python

@data_fixture("products.csv", description="Product list")
def product_list(data):
    return [p for p in data if p["available"] == "true"]

```
