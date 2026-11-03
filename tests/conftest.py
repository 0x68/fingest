import pytest

from fingest import (
    BaseFixture,
    CSVFixture,
    JSONFixture,
    XMLFixture,
    aws_bucket_fixture,
    azure_blob_fixture,
    data_fixture,
    gcs_fixture,
)

# -- local data files ---------------------------------------------------------


@data_fixture("test.json", description="JSON File Foo Bar")
class JsonData(JSONFixture): ...


@data_fixture("test.xml", description="XML File Foo Bar")
class XMLData(BaseFixture): ...


@data_fixture("test.csv", description="CSV File FOO Bar")
class CSV(BaseFixture):
    """CSV File"""


@data_fixture("users.json", description="User data from JSON")
class user_data(JSONFixture):
    pass


@data_fixture("products.csv", description="Product data from CSV")
class product_data(CSVFixture):
    pass


@data_fixture("config.xml", description="Configuration from XML")
class config_data(XMLFixture):
    pass


@data_fixture("test.json", description="Simple JSON test data")
class simple_data(BaseFixture):
    pass


@data_fixture("users.json")
def user_function_data(data):
    return data


@data_fixture("products.csv")
def product_function_data(data):
    return data


@pytest.fixture
def mock_dependency():
    return "dependency_value"


@pytest.fixture
def another_dependency():
    return {"key": "value"}


@data_fixture("test.json")
def function_with_deps(data, mock_dependency, another_dependency):
    return {
        "data": data,
        "mock_dep": mock_dependency,
        "another_dep": another_dependency,
        "combined": f"{mock_dependency}_{data.get('Foo', 'unknown')}",
    }


@data_fixture("test.json")
def function_with_optional_deps(data, mock_dependency, optional_param="default"):
    return {"data": data, "mock_dep": mock_dependency, "optional": optional_param}


@data_fixture("test.json")
def function_with_varargs(data, mock_dependency, *args, **kwargs):
    return {"data": data, "dep": mock_dependency, "args": args, "kwargs": kwargs}


@data_fixture("test.json")
def function_with_request(data, request):
    return request.node.name


TEARDOWN_LOG: list[str] = []


@data_fixture("test.json")
def generator_fixture(data):
    TEARDOWN_LOG.append("setup")
    yield data
    TEARDOWN_LOG.append("teardown")


@data_fixture("users.json", scope="session", name="session_users")
class SessionUsers(JSONFixture):
    instances = 0

    def __init__(self, data, **kwargs):
        super().__init__(data, **kwargs)
        type(self).instances += 1


# -- cloud objects (served from tests/data/<provider>/<bucket>/<key>) --------


@aws_bucket_fixture("reports", "users.json", description="S3 users")
class s3_users(JSONFixture):
    pass


@aws_bucket_fixture("reports", "2026/11/sales.csv")
class s3_sales(CSVFixture):
    pass


@gcs_fixture("analytics", "events/day1.jsonl")
def gcs_events(data):
    return data


@gcs_fixture("analytics", "products.csv", scope="module")
class gcs_products(CSVFixture):
    pass


@azure_blob_fixture("configs", "app/config.xml")
class azure_config(XMLFixture):
    pass
