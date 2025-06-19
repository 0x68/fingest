from fingest.plugin import data_fixture
from fingest.types import BaseFixture, JSONFixture


@data_fixture("test.json", description="Das ist ein Test der fehl schlaegt")
class JsonData(JSONFixture): ...


@data_fixture("test.xml", description="Das ist ein Test der fehl schlaegt")
class XMLData(BaseFixture): ...


@data_fixture("test.csv", description="CSV File which is Dirty as Fck")
class CSV(BaseFixture):
    """CSV File"""

    ...


@data_fixture("test.json", description="Func Bases")
def json_test_file(data):
    return data
