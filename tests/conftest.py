from fingest.plugin import data_fixture
from fingest.types import BaseFixture, JSONFixture, CSVFixture, XMLFixture
from fingest import gcs_fixture


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


# Additional test fixtures for comprehensive testing
@data_fixture("users.json", description="User data from JSON")
class user_data(JSONFixture):
    """Test fixture for user data."""
    pass


@data_fixture("products.csv", description="Product data from CSV")
class product_data(CSVFixture):
    """Test fixture for product data."""
    pass


@data_fixture("config.xml", description="Configuration from XML")
class config_data(XMLFixture):
    """Test fixture for configuration data."""
    pass


@data_fixture("test.json", description="Simple JSON test data")
class simple_data(BaseFixture):
    """Test fixture using base class."""
    pass


# Test function-based fixtures
@data_fixture("users.json", description="User data as function")
def user_function_data(data):
    """Function-based fixture for user data."""
    return data


@data_fixture("products.csv", description="Product data as function")
def product_function_data(data):
    """Function-based fixture for product data."""
    return data


# Additional fixtures for testing signature preservation
import pytest


@pytest.fixture
def mock_dependency():
    """A mock dependency fixture."""
    return "dependency_value"


@pytest.fixture
def another_dependency():
    """Another mock dependency fixture."""
    return {"key": "value"}


@pytest.fixture
def required_dep():
    """A required dependency fixture for complex signature tests."""
    return "required_dependency_value"


# Test function-based fixture with dependencies
@data_fixture("test.json", description="Function fixture with dependencies")
def function_with_deps(data, mock_dependency, another_dependency):
    """Function fixture that depends on other fixtures."""
    return {
        "data": data,
        "mock_dep": mock_dependency,
        "another_dep": another_dependency,
        "combined": f"{mock_dependency}_{data.get('Foo', 'unknown')}"
    }


# Test function-based fixture with optional dependencies
@data_fixture("test.json", description="Function fixture with optional dependencies")
def function_with_optional_deps(data, mock_dependency, optional_param="default_value"):
    """Function fixture with optional parameters."""
    return {
        "data": data,
        "mock_dep": mock_dependency,
        "optional": optional_param
    }


# Test function-based fixture with complex signature
@data_fixture("test.json", description="Function fixture with complex signature")
def function_with_complex_sig(data, required_dep, optional_dep="default", *args, **kwargs):
    """Function fixture with complex signature including *args and **kwargs."""
    return {
        "data": data,
        "required": required_dep,
        "optional": optional_dep,
        "args": args,
        "kwargs": kwargs
    }


@gcs_fixture(bucket="my-bucket", key="test.json")
def gcs_bucket(data):
    return data
