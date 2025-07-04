import pytest
from lxml import etree
from fingest.types import BaseFixture, JSONFixture, CSVFixture, XMLFixture

 
def test_initialization():
    """Test BaseFixture initialization."""
    data = {"test": "data"}
    fixture = BaseFixture(data)
    assert fixture.data == data
    assert fixture._data == data

def test_len_with_list():
    """Test __len__ with list data."""
    data = [1, 2, 3, 4, 5]
    fixture = BaseFixture(data)
    assert len(fixture) == 5

def test_len_with_dict():
    """Test __len__ with dict data."""
    data = {"a": 1, "b": 2, "c": 3}
    fixture = BaseFixture(data)
    assert len(fixture) == 3

def test_len_with_string():
    """Test __len__ with string data."""
    data = "hello"
    fixture = BaseFixture(data)
    assert len(fixture) == 5

def test_len_with_non_sized_object():
    """Test __len__ with object that doesn't support len()."""
    data = 42
    fixture = BaseFixture(data)
    assert len(fixture) == 0

def test_bool_with_empty_data():
    """Test __bool__ with empty data."""
    empty_list = BaseFixture([])
    empty_dict = BaseFixture({})
    empty_string = BaseFixture("")
    none_data = BaseFixture(None)
    
    assert bool(empty_list) is False
    assert bool(empty_dict) is False
    assert bool(empty_string) is False
    assert bool(none_data) is False

def test_bool_with_non_empty_data():
    """Test __bool__ with non-empty data."""
    list_data = BaseFixture([1, 2, 3])
    dict_data = BaseFixture({"key": "value"})
    string_data = BaseFixture("hello")
    number_data = BaseFixture(42)
    
    assert bool(list_data) is True
    assert bool(dict_data) is True
    assert bool(string_data) is True
    assert bool(number_data) is True

def test_bool_with_non_sized_object():
    """Test __bool__ with object that doesn't support len()."""
    data = object()
    fixture = BaseFixture(data)
    assert bool(fixture) is True

def test_repr():
    """Test __repr__ method."""
    data = {"test": "data"}
    fixture = BaseFixture(data)
    repr_str = repr(fixture)
    assert "BaseFixture" in repr_str
    assert "data=" in repr_str

def test_repr_with_description():
    """Test __repr__ with description shows description instead of data."""
    fixture = BaseFixture({"a": 1}, description="my desc")
    assert repr(fixture) == "BaseFixture('my desc')"

def test_repr_truncates_long_data():
    """Test __repr__ truncates data exceeding 80 chars."""
    big_data = {f"key_{i}": f"value_{i}" for i in range(50)}
    fixture = BaseFixture(big_data)
    r = repr(fixture)
    # repr should be reasonably short, not a wall of text
    assert len(r) < 200
    assert "..." in r

def test_str_truncates_long_data():
    """Test __str__ truncates data exceeding 80 chars."""
    big_data = list(range(100))
    fixture = BaseFixture(big_data, description="big list")
    s = str(fixture)
    assert "..." in s
    assert "big list" in s

def test_iter_with_list():
    """Test __iter__ with list data."""
    data = [1, 2, 3]
    fixture = BaseFixture(data)
    assert list(fixture) == [1, 2, 3]

def test_iter_with_dict():
    """Test __iter__ with dict iterates over keys."""
    data = {"a": 1, "b": 2}
    fixture = BaseFixture(data)
    assert set(fixture) == {"a", "b"}

def test_iter_with_string():
    """Test __iter__ with string data."""
    fixture = BaseFixture("abc")
    assert list(fixture) == ["a", "b", "c"]

def test_contains_with_list():
    """Test __contains__ with list data."""
    fixture = BaseFixture([10, 20, 30])
    assert 20 in fixture
    assert 99 not in fixture

def test_contains_with_dict():
    """Test __contains__ with dict checks keys."""
    fixture = BaseFixture({"x": 1, "y": 2})
    assert "x" in fixture
    assert "z" not in fixture

def test_contains_with_string():
    """Test __contains__ with string data."""
    fixture = BaseFixture("hello world")
    assert "hello" in fixture
    assert "xyz" not in fixture

def test_eq_same_data():
    """Test __eq__ with identical data and description."""
    a = BaseFixture({"k": "v"}, description="test")
    b = BaseFixture({"k": "v"}, description="test")
    assert a == b

def test_eq_different_data():
    """Test __eq__ with different data."""
    a = BaseFixture([1, 2])
    b = BaseFixture([3, 4])
    assert a != b

def test_eq_different_description():
    """Test __eq__ with different descriptions."""
    a = BaseFixture([1], description="one")
    b = BaseFixture([1], description="two")
    assert a != b

def test_eq_not_a_fixture():
    """Test __eq__ returns NotImplemented for non-fixture objects."""
    fixture = BaseFixture([1])
    assert fixture != "not a fixture"
    assert fixture != 42

def test_initialization_with_dict():
    """Test JSONFixture initialization with dict."""
    data = {"name": "John", "age": 30}
    fixture = JSONFixture(data)
    assert fixture.data == data

def test_initialization_with_list():
    """Test JSONFixture initialization with list."""
    data = [{"id": 1}, {"id": 2}]
    fixture = JSONFixture(data)
    assert fixture.data == data

def test_keys_with_dict():
    """Test keys() method with dict data."""
    data = {"name": "John", "age": 30, "city": "NYC"}
    fixture = JSONFixture(data)
    keys = list(fixture.keys())
    assert set(keys) == {"name", "age", "city"}

def test_keys_with_list_raises_error():
    """Test keys() method with list data raises TypeError."""
    data = [{"id": 1}, {"id": 2}]
    fixture = JSONFixture(data)
    with pytest.raises(TypeError, match="Data is not a dictionary"):
        fixture.keys()

def test_values_with_dict():
    """Test values() method with dict data."""
    data = {"name": "John", "age": 30}
    fixture = JSONFixture(data)
    values = list(fixture.values())
    assert set(values) == {"John", 30}

def test_values_with_list_raises_error():
    """Test values() method with list data raises TypeError."""
    data = [{"id": 1}, {"id": 2}]
    fixture = JSONFixture(data)
    with pytest.raises(TypeError, match="Data is not a dictionary"):
        fixture.values()

def test_items_with_dict():
    """Test items() method with dict data."""
    data = {"name": "John", "age": 30}
    fixture = JSONFixture(data)
    items = list(fixture.items())
    assert set(items) == {("name", "John"), ("age", 30)}

def test_items_with_list_raises_error():
    """Test items() method with list data raises TypeError."""
    data = [{"id": 1}, {"id": 2}]
    fixture = JSONFixture(data)
    with pytest.raises(TypeError, match="Data is not a dictionary"):
        fixture.items()

def test_get_with_dict():
    """Test get() method with dict data."""
    data = {"name": "John", "age": 30}
    fixture = JSONFixture(data)
    assert fixture.get("name") == "John"
    assert fixture.get("nonexistent") is None
    assert fixture.get("nonexistent", "default") == "default"

def test_get_with_list_raises_error():
    """Test get() method with list data raises TypeError."""
    data = [{"id": 1}, {"id": 2}]
    fixture = JSONFixture(data)
    with pytest.raises(TypeError, match="Data is not a dictionary"):
        fixture.get("key")

def test_length():
    """Test length() method."""
    dict_data = {"a": 1, "b": 2, "c": 3}
    list_data = [1, 2, 3, 4, 5]
    
    dict_fixture = JSONFixture(dict_data)
    list_fixture = JSONFixture(list_data)
    
    assert dict_fixture.length() == 3
    assert list_fixture.length() == 5

def test_getitem_with_dict():
    """Test __getitem__ with dict data."""
    data = {"name": "John", "age": 30}
    fixture = JSONFixture(data)
    assert fixture["name"] == "John"
    assert fixture["age"] == 30

def test_getitem_with_list():
    """Test __getitem__ with list data."""
    data = [{"id": 1}, {"id": 2}, {"id": 3}]
    fixture = JSONFixture(data)
    assert fixture[0] == {"id": 1}
    assert fixture[1] == {"id": 2}
    assert fixture[2] == {"id": 3}

def test_iter_with_dict():
    """Test __iter__ on dict-backed JSONFixture iterates over keys."""
    fixture = JSONFixture({"a": 1, "b": 2, "c": 3})
    assert set(fixture) == {"a", "b", "c"}

def test_iter_with_list():
    """Test __iter__ on list-backed JSONFixture iterates over items."""
    fixture = JSONFixture([10, 20, 30])
    assert list(fixture) == [10, 20, 30]

def test_contains_with_dict():
    """Test __contains__ checks keys for dict data."""
    fixture = JSONFixture({"name": "John", "age": 30})
    assert "name" in fixture
    assert "missing" not in fixture

def test_contains_with_list():
    """Test __contains__ checks items for list data."""
    fixture = JSONFixture([1, 2, 3])
    assert 2 in fixture
    assert 99 not in fixture


def test_initialization():
    """Test CSVFixture initialization."""
    data = [
        {"name": "John", "age": "30"},
        {"name": "Jane", "age": "25"}
    ]
    fixture = CSVFixture(data)
    assert fixture.data == data

def test_rows_property():
    """Test rows property."""
    data = [
        {"name": "John", "age": "30"},
        {"name": "Jane", "age": "25"}
    ]
    fixture = CSVFixture(data)
    assert fixture.rows == data

def test_row_count_property():
    """Test row_count property."""
    data = [
        {"name": "John", "age": "30"},
        {"name": "Jane", "age": "25"},
        {"name": "Bob", "age": "35"},
    ]
    fixture = CSVFixture(data)
    assert fixture.row_count == 3

def test_row_count_empty():
    """Test row_count on empty data."""
    fixture = CSVFixture([])
    assert fixture.row_count == 0

def test_columns_property():
    """Test columns property."""
    data = [
        {"name": "John", "age": "30", "city": "NYC"},
        {"name": "Jane", "age": "25", "city": "LA"}
    ]
    fixture = CSVFixture(data)
    assert fixture.columns == ["name", "age", "city"]

def test_columns_property_empty_data():
    """Test columns property with empty data."""
    fixture = CSVFixture([])
    assert fixture.columns == []

def test_get_column():
    """Test get_column method."""
    data = [
        {"name": "John", "age": "30"},
        {"name": "Jane", "age": "25"},
        {"name": "Bob", "age": "35"}
    ]
    fixture = CSVFixture(data)
    names = fixture.get_column("name")
    ages = fixture.get_column("age")
    
    assert names == ["John", "Jane", "Bob"]
    assert ages == ["30", "25", "35"]

def test_get_column_missing_key():
    """Test get_column with missing key."""
    data = [
        {"name": "John", "age": "30"},
        {"name": "Jane"}  # Missing age
    ]
    fixture = CSVFixture(data)
    ages = fixture.get_column("age")
    assert ages == ["30", ""]

def test_filter_rows():
    """Test filter_rows method."""
    data = [
        {"name": "John", "age": "30", "city": "NYC"},
        {"name": "Jane", "age": "25", "city": "LA"},
        {"name": "Bob", "age": "30", "city": "NYC"}
    ]
    fixture = CSVFixture(data)
    
    # Filter by age
    age_30 = fixture.filter_rows(age="30")
    assert len(age_30) == 2
    assert age_30[0]["name"] == "John"
    assert age_30[1]["name"] == "Bob"
    
    # Filter by city
    nyc_residents = fixture.filter_rows(city="NYC")
    assert len(nyc_residents) == 2
    
    # Filter by multiple criteria
    nyc_30 = fixture.filter_rows(age="30", city="NYC")
    assert len(nyc_30) == 2

def test_filter_rows_no_matches():
    """Test filter_rows with no matches."""
    data = [
        {"name": "John", "age": "30"},
        {"name": "Jane", "age": "25"}
    ]
    fixture = CSVFixture(data)
    result = fixture.filter_rows(age="40")
    assert result == []

def test_filter_rows_with_callable_predicate():
    """Test filter_rows with a callable predicate instead of literal value."""
    data = [
        {"name": "Laptop", "price": "999.99"},
        {"name": "Mouse", "price": "29.99"},
        {"name": "Monitor", "price": "499.99"},
    ]
    fixture = CSVFixture(data)

    expensive = fixture.filter_rows(price=lambda p: float(p) > 100)
    assert len(expensive) == 2
    assert expensive[0]["name"] == "Laptop"
    assert expensive[1]["name"] == "Monitor"

def test_filter_rows_mixed_callable_and_literal():
    """Test filter_rows mixing callable predicates and literal values."""
    data = [
        {"name": "A", "category": "X", "score": "80"},
        {"name": "B", "category": "X", "score": "40"},
        {"name": "C", "category": "Y", "score": "90"},
    ]
    fixture = CSVFixture(data)

    result = fixture.filter_rows(
        category="X",
        score=lambda s: int(s) > 50,
    )
    assert len(result) == 1
    assert result[0]["name"] == "A"

def test_getitem():
    """Test __getitem__ method."""
    data = [
        {"name": "John", "age": "30"},
        {"name": "Jane", "age": "25"}
    ]
    fixture = CSVFixture(data)
    assert fixture[0] == {"name": "John", "age": "30"}
    assert fixture[1] == {"name": "Jane", "age": "25"}

def test_iter():
    """Test __iter__ iterates over rows."""
    data = [
        {"name": "John"},
        {"name": "Jane"},
    ]
    fixture = CSVFixture(data)
    names = [row["name"] for row in fixture]
    assert names == ["John", "Jane"]

def test_contains_row():
    """Test __contains__ checks for row membership."""
    data = [
        {"name": "John", "age": "30"},
        {"name": "Jane", "age": "25"},
    ]
    fixture = CSVFixture(data)
    assert {"name": "John", "age": "30"} in fixture
    assert {"name": "Bob", "age": "40"} not in fixture


def test_initialization():
    """Test XMLFixture initialization."""
    xml_string = "<root><item>test</item></root>"
    tree = etree.fromstring(xml_string)
    element_tree = etree.ElementTree(tree)
    
    fixture = XMLFixture(element_tree)
    assert fixture.data == element_tree

def test_root_property():
    """Test root property."""
    xml_string = "<configuration><setting>value</setting></configuration>"
    tree = etree.fromstring(xml_string)
    element_tree = etree.ElementTree(tree)
    
    fixture = XMLFixture(element_tree)
    root = fixture.root
    assert root.tag == "configuration"

def test_tag_property():
    """Test tag shortcut property."""
    xml_string = "<myroot><child/></myroot>"
    tree = etree.fromstring(xml_string)
    element_tree = etree.ElementTree(tree)

    fixture = XMLFixture(element_tree)
    assert fixture.tag == "myroot"

def test_find_method():
    """Test find method."""
    xml_string = """
    <config>
        <database>
            <host>localhost</host>
            <port>5432</port>
        </database>
    </config>
    """
    tree = etree.fromstring(xml_string)
    element_tree = etree.ElementTree(tree)
    
    fixture = XMLFixture(element_tree)
    host = fixture.find("database/host")
    assert host is not None
    assert host.text == "localhost"
    
    # Test non-existent element
    missing = fixture.find("database/missing")
    assert missing is None

def test_findall_method():
    """Test findall method."""
    xml_string = """
    <config>
        <items>
            <item>first</item>
            <item>second</item>
            <item>third</item>
        </items>
    </config>
    """
    tree = etree.fromstring(xml_string)
    element_tree = etree.ElementTree(tree)
    
    fixture = XMLFixture(element_tree)
    items = fixture.findall("items/item")
    assert len(items) == 3
    assert items[0].text == "first"
    assert items[1].text == "second"
    assert items[2].text == "third"

def test_xpath_method():
    """Test xpath method."""
    xml_string = """
    <config>
        <features>
            <feature name="logging" enabled="true"/>
            <feature name="caching" enabled="false"/>
            <feature name="monitoring" enabled="true"/>
        </features>
    </config>
    """
    tree = etree.fromstring(xml_string)
    element_tree = etree.ElementTree(tree)
    
    fixture = XMLFixture(element_tree)
    enabled_features = fixture.xpath("//feature[@enabled='true']")
    assert len(enabled_features) == 2
    
    feature_names = [f.get("name") for f in enabled_features]
    assert "logging" in feature_names
    assert "monitoring" in feature_names

def test_get_text_method():
    """Test get_text method."""
    xml_string = """
    <config>
        <settings>
            <timeout>30</timeout>
            <retries>3</retries>
            <empty></empty>
        </settings>
    </config>
    """
    tree = etree.fromstring(xml_string)
    element_tree = etree.ElementTree(tree)
    
    fixture = XMLFixture(element_tree)
    
    # Test existing elements
    timeout = fixture.get_text("settings/timeout")
    assert timeout == "30"
    
    retries = fixture.get_text("settings/retries")
    assert retries == "3"
    
    # Test empty element
    empty = fixture.get_text("settings/empty")
    assert empty == ""
    
    # Test non-existent element with default
    missing = fixture.get_text("settings/missing", "default")
    assert missing == "default"
    
    # Test non-existent element without default
    missing_no_default = fixture.get_text("settings/missing")
    assert missing_no_default == ""

def test_to_dict_simple():
    """Test to_dict with a simple XML structure."""
    xml_string = """
    <config>
        <host>localhost</host>
        <port>5432</port>
    </config>
    """
    tree = etree.fromstring(xml_string)
    element_tree = etree.ElementTree(tree)
    fixture = XMLFixture(element_tree)

    d = fixture.to_dict()
    assert d["config"]["host"] == "localhost"
    assert d["config"]["port"] == "5432"

def test_to_dict_with_attributes():
    """Test to_dict preserves element attributes under @key."""
    xml_string = '<item id="1" active="true">hello</item>'
    tree = etree.fromstring(xml_string)
    element_tree = etree.ElementTree(tree)
    fixture = XMLFixture(element_tree)

    d = fixture.to_dict()
    assert d["item"]["@id"] == "1"
    assert d["item"]["@active"] == "true"
    assert d["item"]["#text"] == "hello"

def test_to_dict_with_repeated_children():
    """Test to_dict collapses repeated tags into a list."""
    xml_string = """
    <root>
        <item>one</item>
        <item>two</item>
        <item>three</item>
    </root>
    """
    tree = etree.fromstring(xml_string)
    element_tree = etree.ElementTree(tree)
    fixture = XMLFixture(element_tree)

    d = fixture.to_dict()
    items = d["root"]["item"]
    assert isinstance(items, list)
    assert len(items) == 3
    assert items[0] == "one"
    assert items[2] == "three"

def test_to_dict_nested():
    """Test to_dict with nested elements."""
    xml_string = """
    <config>
        <database>
            <host>localhost</host>
            <port>5432</port>
        </database>
    </config>
    """
    tree = etree.fromstring(xml_string)
    element_tree = etree.ElementTree(tree)
    fixture = XMLFixture(element_tree)

    d = fixture.to_dict()
    db = d["config"]["database"]
    assert db["host"] == "localhost"
    assert db["port"] == "5432"
