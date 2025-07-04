from fingest.plugin import data_fixture
from fingest.types import BaseFixture, JSONFixture, CSVFixture, XMLFixture


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
