# Fingest — Pytest Data-Driven Fixtures

[![PyPI version](https://badge.fury.io/py/fingest.svg)](https://badge.fury.io/py/fingest)
[![Python versions](https://img.shields.io/pypi/pyversions/fingest.svg)](https://pypi.org/project/fingest/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A pytest plugin that turns **JSON, CSV, and XML files** into fully-typed, iterable test fixtures — no boilerplate required.

## Quick Start

### 1. Install

```bash
pip install fingest
```

### 2. Point pytest at your data

```ini
# pytest.ini  (or pyproject.toml under [tool.pytest.ini_options])
[pytest]
fingest_fixture_path = tests/data
```

### 3. Define fixtures in `conftest.py`

```python
from fingest import data_fixture, JSONFixture, CSVFixture, XMLFixture

@data_fixture("users.json", description="Test user data")
class user_data(JSONFixture):
    pass

@data_fixture("products.csv", description="Product catalog")
class product_data(CSVFixture):
    pass

@data_fixture("config.xml", description="App configuration")
class config_data(XMLFixture):
    pass
```

### 4. Use them in tests

```python
def test_users(user_data):
    assert len(user_data) == 2
    assert "Alice" in [u["name"] for u in user_data]  # iterable!

def test_expensive_products(product_data):
    expensive = product_data.filter_rows(price=lambda p: float(p) > 100)
    assert len(expensive) >= 1

def test_db_host(config_data):
    assert config_data.get_text("database/host") == "localhost"
```

---

## Fixture Types

### `BaseFixture`

All fixtures inherit from `BaseFixture`, which gives you:

| Feature | Example |
|---|---|
| Length | `len(fixture)` |
| Truthiness | `if fixture:` |
| Iteration | `for item in fixture:` |
| Containment | `"key" in fixture` |
| Equality | `fixture_a == fixture_b` |
| Raw data | `fixture.data` |

### `JSONFixture`

For dict or list JSON data.

```python
fixture["users"]          # direct indexing
fixture.get("key", None)  # safe access
fixture.keys()            # dict keys
for key in fixture:       # iterate keys (dict) or items (list)
"name" in fixture         # containment check
```

### `CSVFixture`

For tabular CSV data.

```python
fixture.rows              # all rows as list of dicts
fixture.row_count         # number of rows
fixture.columns           # column names
fixture.get_column("age") # all values from one column
fixture[0]                # first row

# filter with exact values or predicates
fixture.filter_rows(city="NYC")
fixture.filter_rows(price=lambda p: float(p) > 100)

for row in fixture:       # iterate rows
{"name": "Bob"} in fixture  # row membership
```

### `XMLFixture`

For XML data, powered by lxml.

```python
fixture.root              # root Element
fixture.tag               # root tag name
fixture.find("db/host")   # first matching element
fixture.findall("items/item")  # all matches
fixture.xpath("//feature[@enabled='true']")
fixture.get_text("settings/timeout", default="30")
fixture.to_dict()         # recursive XML → dict conversion
```

---

## Cloud Storage Adapters

Fingest includes decorators for **AWS S3**, **GCP GCS**, and **Azure Blob Storage**. These are designed for **mock-first development**: by default, they load data from your local `fingest_fixture_path`, simulating cloud responses.

### 1. Define Cloud Fixtures

```python
from fingest import aws_bucket_fixture, gcs_fixture, azure_blob_fixture
from fingest import JSONFixture, CSVFixture, XMLFixture

# AWS S3 (Bucket: "my-bucket", Key: "data/users.json")
@aws_bucket_fixture("my-bucket", "data/users.json", description="S3 users")
class s3_users(JSONFixture): pass

# GCP GCS (Bucket: "my-bucket", Key: "data/products.csv")
@gcs_fixture("my-bucket", "data/products.csv", description="GCS products")
class gcs_products(CSVFixture): pass

# Azure Blob (Container: "my-container", Blob: "data/config.xml")
@azure_blob_fixture("my-container", "data/config.xml", description="Azure config")
class azure_config(XMLFixture): pass
```

### 2. Mocking vs. Live Mode

The adapters are in **mock mode** by default. They will look for files in your local fixture directory using the key as a relative path (e.g., `tests/data/data/users.json` for the examples above).

To enable **live mode** (hitting the real cloud SDKs), set `mock=False`. Note that cloud SDKs (`boto3`, `google-cloud-storage`, `azure-storage-blob`) are optional dependencies and must be installed separately.

```python
@aws_bucket_fixture("my-bucket", "data/users.json", mock=False)
class live_s3_data(JSONFixture): pass
```

---

## Function-Based Fixtures

For custom data transformations or fixtures that depend on other pytest fixtures:

```python
@data_fixture("raw_data.json")
def processed_users(data):
    """data is injected by fingest; remaining params are pytest fixtures."""
    return [{"name": f"{u['first']} {u['last']}"} for u in data["users"]]

@data_fixture("config.json")
def config_with_db(data, database_fixture):
    """Depends on another pytest fixture — works seamlessly."""
    return {"config": data, "db": database_fixture}
```

## Custom Data Loaders

Support any file format by registering a loader:

```python
from fingest import register_loader
import yaml

def yaml_loader(path):
    with open(path) as f:
        return yaml.safe_load(f)

register_loader("yaml", yaml_loader)
```

Or use a one-off loader for a single fixture:

```python
@data_fixture("data.toml", loader=toml_loader)
class toml_config(BaseFixture):
    pass
```

---

## API Reference

### `@data_fixture(file_path, description="", loader=None)`

Register a class or function as a data-driven fixture.

| Parameter | Type | Description |
|---|---|---|
| `file_path` | `str` | Path to data file, relative to `fingest_fixture_path` |
| `description` | `str` | Optional label for debugging / docs |
| `loader` | `callable` | Optional custom loader `(Path) → Any` |

### `register_loader(extension, loader_func)`

Register a custom data loader globally for a file extension (without dot).

### Base Classes

| Class | Key Methods |
|---|---|
| `BaseFixture` | `data`, `description`, `len()`, `bool()`, `iter()`, `in`, `==` |
| `JSONFixture` | `keys()`, `values()`, `items()`, `get()`, `length()`, `[]` |
| `CSVFixture` | `rows`, `row_count`, `columns`, `get_column()`, `filter_rows()`, `[]` |
| `XMLFixture` | `root`, `tag`, `find()`, `findall()`, `xpath()`, `get_text()`, `to_dict()` |

---

## Development

```bash
git clone https://github.com/0x68/fingest.git
cd fingest
uv sync
uv run pytest
```

## License

MIT — see [LICENSE](LICENSE).

---

**Made with ❤️ by [Tim Fiedler](https://github.com/0x68)**
