import pytest


@pytest.fixture
def fingest():
    return True

def test_data_fixture(JsonData):
    assert JsonData.data.get("Foo") == "Bari"


def test_data_fixtute(JsonData):
    assert JsonData.length() == 1


def test_csv(CSV):
    assert len(CSV.data) == 5


def test_json_func(json_test_file):
    assert json_test_file.get("Foo") == "Bar"
