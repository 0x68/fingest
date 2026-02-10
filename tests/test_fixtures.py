"""Tests for fingest data fixtures."""

import pytest
from pathlib import Path

# Test fixtures are defined in conftest.py and will be automatically available


class TestJSONFixtures:
    """Test JSON-based fixtures."""

    def test_user_data_basic(self, user_data):
        """Test basic user data access."""
        assert user_data is not None
        assert len(user_data) == 3
        assert user_data.length() == 3

    def test_user_data_keys(self, user_data):
        """Test accessing JSON keys."""
        # user_data contains a list, so we test the first item
        first_user = user_data[0]
        expected_keys = {"id", "name", "email", "age", "active"}
        assert set(first_user.keys()) == expected_keys

    def test_user_data_indexing(self, user_data):
        """Test indexing into user data."""
        first_user = user_data[0]
        assert first_user["name"] == "John Doe"
        assert first_user["age"] == 30
        assert first_user["active"] is True

    def test_simple_data_get(self, simple_data):
        """Test get method on simple JSON data."""
        # simple_data uses test.json which contains {"Foo": "Bar"}
        assert simple_data.data.get("Foo") == "Bar"
        assert simple_data.data.get("NonExistent", "default") == "default"
    
    def test_user_function_data(self, user_function_data):
        """Test function-based JSON fixture."""
        assert isinstance(user_function_data, list)
        assert len(user_function_data) == 3
        assert user_function_data[0]["name"] == "John Doe"


class TestCSVFixtures:
    """Test CSV-based fixtures."""

    def test_product_data_basic(self, product_data):
        """Test basic product data access."""
        assert product_data is not None
        assert len(product_data) == 5
        assert len(product_data.rows) == 5

    def test_product_data_columns(self, product_data):
        """Test CSV column access."""
        expected_columns = ["id", "name", "price", "category", "in_stock"]
        assert product_data.columns == expected_columns

    def test_product_data_column_values(self, product_data):
        """Test getting column values."""
        names = product_data.get_column("name")
        expected_names = ["Laptop", "Mouse", "Keyboard", "Desk", "Chair"]
        assert names == expected_names

    def test_product_data_filtering(self, product_data):
        """Test filtering CSV data."""
        electronics = product_data.filter_rows(category="Electronics")
        assert len(electronics) == 3

        in_stock = product_data.filter_rows(in_stock="true")
        assert len(in_stock) == 4

    def test_product_data_indexing(self, product_data):
        """Test indexing into CSV data."""
        first_product = product_data[0]
        assert first_product["name"] == "Laptop"
        assert first_product["price"] == "999.99"
    
    def test_product_function_data(self, product_function_data):
        """Test function-based CSV fixture."""
        assert isinstance(product_function_data, list)
        assert len(product_function_data) == 5
        assert product_function_data[0]["name"] == "Laptop"


class TestXMLFixtures:
    """Test XML-based fixtures."""

    def test_config_data_basic(self, config_data):
        """Test basic XML data access."""
        assert config_data is not None
        assert config_data.root is not None
        assert config_data.root.tag == "configuration"

    def test_config_data_find(self, config_data):
        """Test finding XML elements."""
        host = config_data.find("database/host")
        assert host is not None
        assert host.text == "localhost"

        port = config_data.find("database/port")
        assert port is not None
        assert port.text == "5432"

    def test_config_data_findall(self, config_data):
        """Test finding all matching XML elements."""
        features = config_data.findall("features/feature")
        assert len(features) == 3

        # Check feature names
        feature_names = [f.get("name") for f in features]
        expected_names = ["logging", "caching", "monitoring"]
        assert feature_names == expected_names

    def test_config_data_get_text(self, config_data):
        """Test getting text content from XML."""
        timeout = config_data.get_text("settings/timeout")
        assert timeout == "30"

        # Test default value
        missing = config_data.get_text("settings/missing", "default")
        assert missing == "default"

    def test_config_data_xpath(self, config_data):
        """Test XPath queries."""
        enabled_features = config_data.xpath("//feature[@enabled='true']")
        assert len(enabled_features) == 2

        # Check that logging and monitoring are enabled
        enabled_names = [f.get("name") for f in enabled_features]
        assert "logging" in enabled_names
        assert "monitoring" in enabled_names


class TestFixtureDescriptions:
    """Test fixture descriptions and metadata."""

    def test_fixture_description(self, user_data):
        """Test that fixture contains description."""
        assert hasattr(user_data, 'description')
        assert user_data.description == "User data from JSON"

    def test_fixture_str(self, user_data):
        """Test string representation of fixture."""
        str_repr = str(user_data)
        assert "User data from JSON" in str_repr


class TestBaseFixture:
    """Test BaseFixture functionality."""

    def test_base_fixture_bool(self, simple_data):
        """Test boolean evaluation of fixtures."""
        assert bool(simple_data) is True

    def test_base_fixture_len(self, simple_data):
        """Test length of fixtures."""
        # simple_data contains {"Foo": "Bar"}, so length should be 1
        assert len(simple_data) == 1

    def test_base_fixture_repr(self, simple_data):
        """Test string representation of fixtures."""
        repr_str = repr(simple_data)
        assert "Simple JSON test data" in repr_str
