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
