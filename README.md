# Fingest - Pytest Data-Driven Fixtures Plugin

[![PyPI version](https://badge.fury.io/py/fingest.svg)](https://badge.fury.io/py/fingest)
[![Python versions](https://img.shields.io/pypi/pyversions/fingest.svg)](https://pypi.org/project/fingest/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Fingest is a powerful pytest plugin that enables **data-driven testing** by automatically creating fixtures from external data files. It supports JSON, CSV, and XML formats out of the box, with extensible support for custom data loaders.

## ✨ Features

- 🚀 **Automatic fixture registration** from data files
- 📁 **Multiple format support**: JSON, CSV, XML (extensible)
- 🎯 **Type-specific base classes** with rich functionality
- 🔧 **Custom data loaders** for any file format
- 📝 **Descriptive fixtures** for better test documentation
- ⚙️ **Configurable data paths** via pytest.ini
- 🧪 **Comprehensive test coverage** (84 tests, 100% pass rate)

## 📦 Installation

Install from PyPI:

```bash
pip install fingest
```

Or with Poetry:

```bash
poetry add fingest
```

## 🚀 Quick Start

### 1. Configure pytest.ini

```ini
[pytest]
fingest_fixture_path = tests/data  # Path to your data files
```

### 2. Create data files

**users.json**
```json
[
  {"id": 1, "name": "Alice", "email": "alice@example.com"},
  {"id": 2, "name": "Bob", "email": "bob@example.com"}
]
```

**products.csv**
```csv
id,name,price,category
1,Laptop,999.99,Electronics
2,Mouse,29.99,Electronics
```

**config.xml**
```xml
<?xml version="1.0"?>
<config>
    <database>
        <host>localhost</host>
        <port>5432</port>
    </database>
</config>
```

### 3. Define fixtures in conftest.py

```python
from fingest import data_fixture, JSONFixture, CSVFixture, XMLFixture

@data_fixture("users.json", description="Test user data")
class user_data(JSONFixture):
    """Fixture for user test data."""
    pass

@data_fixture("products.csv", description="Product catalog")
class product_data(CSVFixture):
    """Fixture for product data."""
    pass

@data_fixture("config.xml", description="App configuration")
class config_data(XMLFixture):
    """Fixture for configuration data."""
    pass
```

### 4. Use in your tests

```python
def test_user_count(user_data):
    assert len(user_data) == 2
    assert user_data[0]["name"] == "Alice"

def test_product_filtering(product_data):
    electronics = product_data.filter_rows(category="Electronics")
    assert len(electronics) == 2

def test_database_config(config_data):
    host = config_data.get_text("database/host")
    assert host == "localhost"
```

## 📚 Comprehensive Guide

### Fixture Types

Fingest provides specialized fixture classes for different data formats:

#### JSONFixture
For JSON data with dictionary and list operations:

```python
@data_fixture("api_response.json")
class api_data(JSONFixture):
    pass

def test_json_operations(api_data):
    # Access dictionary methods
    assert "users" in api_data.keys()
    user_count = api_data.get("user_count", 0)

    # Direct indexing
    first_user = api_data["users"][0]
    assert first_user["active"] is True
```

#### CSVFixture
For CSV data with row and column operations:

```python
@data_fixture("sales_data.csv")
class sales_data(CSVFixture):
    pass

def test_csv_operations(sales_data):
    # Get all column names
    columns = sales_data.columns
    assert "product_name" in columns

    # Get specific column values
    prices = sales_data.get_column("price")
    assert all(float(p) > 0 for p in prices)

    # Filter rows
    expensive_items = sales_data.filter_rows(price="999.99")
    assert len(expensive_items) > 0
```

#### XMLFixture
For XML data with XPath and element operations:

```python
@data_fixture("settings.xml")
class settings_data(XMLFixture):
    pass

def test_xml_operations(settings_data):
    # Find single elements
    timeout = settings_data.find("timeout")
    assert timeout.text == "30"

    # Find multiple elements
    features = settings_data.findall("features/feature")
    assert len(features) == 3

    # XPath queries
    enabled_features = settings_data.xpath("//feature[@enabled='true']")
    assert len(enabled_features) == 2

    # Get text with default
    debug_mode = settings_data.get_text("debug", "false")
    assert debug_mode in ["true", "false"]
```

### Function-Based Fixtures

You can also create function-based fixtures for custom data processing:

```python
@data_fixture("raw_data.json", description="Processed user data")
def processed_users(data):
    """Transform raw user data."""
    return [
        {
            "id": user["id"],
            "display_name": f"{user['first_name']} {user['last_name']}",
            "email": user["email"].lower()
        }
        for user in data["users"]
    ]

def test_processed_data(processed_users):
    assert processed_users[0]["display_name"] == "John Doe"
    assert "@" in processed_users[0]["email"]
```

### Custom Data Loaders

Extend Fingest to support any file format:

```python
from fingest import register_loader
import yaml

def yaml_loader(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

# Register the loader globally
register_loader("yaml", yaml_loader)

# Or use it for specific fixtures
@data_fixture("config.yaml", loader=yaml_loader)
class yaml_config(BaseFixture):
    pass
```

### Advanced Configuration

#### Multiple Data Directories

```ini
[pytest]
fingest_fixture_path = tests/fixtures
```

#### Environment-Specific Data

```python
import os
from fingest import data_fixture

env = os.getenv("TEST_ENV", "dev")

@data_fixture(f"config_{env}.json", description=f"Config for {env}")
class environment_config(JSONFixture):
    pass
```

## 🔧 API Reference

### Decorators

#### `@data_fixture(file_path, description="", loader=None)`

Register a class or function as a data-driven fixture.

**Parameters:**
- `file_path` (str): Path to data file relative to `fingest_fixture_path`
- `description` (str, optional): Description for debugging and documentation
- `loader` (callable, optional): Custom data loader function

### Base Classes

#### `BaseFixture`
- `data`: Access to raw loaded data
- `__len__()`: Get data length
- `__bool__()`: Check if data exists and is non-empty

#### `JSONFixture(BaseFixture)`
- `keys()`, `values()`, `items()`: Dictionary methods (if data is dict)
- `get(key, default=None)`: Safe key access
- `length()`: Get data length
- `__getitem__(key)`: Direct indexing

#### `CSVFixture(BaseFixture)`
- `rows`: List of all rows
- `columns`: List of column names
- `get_column(name)`: Get all values from a column
- `filter_rows(**kwargs)`: Filter rows by column values
- `__getitem__(index)`: Get row by index

#### `XMLFixture(BaseFixture)`
- `root`: Root XML element
- `find(path)`: Find first element matching XPath
- `findall(path)`: Find all elements matching XPath
- `xpath(path)`: Execute XPath query
- `get_text(path, default="")`: Get text content with default

### Functions

#### `register_loader(extension, loader_func)`

Register a custom data loader for a file extension.

**Parameters:**
- `extension` (str): File extension without dot (e.g., "yaml")
- `loader_func` (callable): Function that takes a Path and returns loaded data

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=fingest

# Run specific test categories
pytest tests/test_types.py      # Test fixture types
pytest tests/test_plugin.py     # Test plugin functionality
pytest tests/test_fixtures.py   # Test fixture integration
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup

```bash
git clone https://github.com/0x68/fingest.git
cd fingest
poetry install
poetry run pytest
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [pytest](https://pytest.org/) plugin architecture
- XML processing powered by [lxml](https://lxml.de/)
- Inspired by the need for better data-driven testing in Python

## 📈 Changelog

### v0.1.0 (Latest)
- ✨ Complete rewrite with improved architecture
- 🚀 Added specialized fixture classes (JSONFixture, CSVFixture, XMLFixture)
- 🔧 Custom data loader support
- 📝 Comprehensive documentation and examples
- 🧪 84 comprehensive tests with 100% pass rate
- 🐛 Fixed critical bugs in data loading and fixture registration
- ⚡ Improved error handling and validation

### v0.0.3
- Basic JSON, CSV, and XML support
- Simple fixture registration

---

**Made with ❤️ by [Tim Fiedler](https://github.com/0x68)**
