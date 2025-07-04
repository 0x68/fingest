"""Tests for fingest type classes."""

import pytest
from lxml import etree
from fingest.types import BaseFixture, JSONFixture, CSVFixture, XMLFixture


class TestBaseFixture:
    """Test BaseFixture class."""
    
    def test_initialization(self):
        """Test BaseFixture initialization."""
        data = {"test": "data"}
        fixture = BaseFixture(data)
        assert fixture.data == data
        assert fixture._data == data
    
    def test_len_with_list(self):
        """Test __len__ with list data."""
        data = [1, 2, 3, 4, 5]
        fixture = BaseFixture(data)
        assert len(fixture) == 5
    
    def test_len_with_dict(self):
        """Test __len__ with dict data."""
        data = {"a": 1, "b": 2, "c": 3}
        fixture = BaseFixture(data)
        assert len(fixture) == 3
    
    def test_len_with_string(self):
        """Test __len__ with string data."""
        data = "hello"
        fixture = BaseFixture(data)
        assert len(fixture) == 5
    
    def test_len_with_non_sized_object(self):
        """Test __len__ with object that doesn't support len()."""
        data = 42
        fixture = BaseFixture(data)
        assert len(fixture) == 0
    
    def test_bool_with_empty_data(self):
        """Test __bool__ with empty data."""
        empty_list = BaseFixture([])
        empty_dict = BaseFixture({})
        empty_string = BaseFixture("")
        none_data = BaseFixture(None)
        
        assert bool(empty_list) is False
        assert bool(empty_dict) is False
        assert bool(empty_string) is False
        assert bool(none_data) is False
    
    def test_bool_with_non_empty_data(self):
        """Test __bool__ with non-empty data."""
        list_data = BaseFixture([1, 2, 3])
        dict_data = BaseFixture({"key": "value"})
        string_data = BaseFixture("hello")
        number_data = BaseFixture(42)
        
        assert bool(list_data) is True
        assert bool(dict_data) is True
        assert bool(string_data) is True
        assert bool(number_data) is True
    
    def test_bool_with_non_sized_object(self):
        """Test __bool__ with object that doesn't support len()."""
        data = object()
        fixture = BaseFixture(data)
        assert bool(fixture) is True
    
    def test_repr(self):
        """Test __repr__ method."""
        data = {"test": "data"}
        fixture = BaseFixture(data)
        repr_str = repr(fixture)
        assert "BaseFixture" in repr_str
        assert "data=" in repr_str


class TestJSONFixture:
    """Test JSONFixture class."""
    
    def test_initialization_with_dict(self):
        """Test JSONFixture initialization with dict."""
        data = {"name": "John", "age": 30}
        fixture = JSONFixture(data)
        assert fixture.data == data
    
    def test_initialization_with_list(self):
        """Test JSONFixture initialization with list."""
        data = [{"id": 1}, {"id": 2}]
        fixture = JSONFixture(data)
        assert fixture.data == data
    
    def test_keys_with_dict(self):
        """Test keys() method with dict data."""
        data = {"name": "John", "age": 30, "city": "NYC"}
        fixture = JSONFixture(data)
        keys = list(fixture.keys())
        assert set(keys) == {"name", "age", "city"}
    
    def test_keys_with_list_raises_error(self):
        """Test keys() method with list data raises TypeError."""
        data = [{"id": 1}, {"id": 2}]
        fixture = JSONFixture(data)
        with pytest.raises(TypeError, match="Data is not a dictionary"):
            fixture.keys()
    
    def test_values_with_dict(self):
        """Test values() method with dict data."""
        data = {"name": "John", "age": 30}
        fixture = JSONFixture(data)
        values = list(fixture.values())
        assert set(values) == {"John", 30}
    
    def test_values_with_list_raises_error(self):
        """Test values() method with list data raises TypeError."""
        data = [{"id": 1}, {"id": 2}]
        fixture = JSONFixture(data)
        with pytest.raises(TypeError, match="Data is not a dictionary"):
            fixture.values()
    
    def test_items_with_dict(self):
        """Test items() method with dict data."""
        data = {"name": "John", "age": 30}
        fixture = JSONFixture(data)
        items = list(fixture.items())
        assert set(items) == {("name", "John"), ("age", 30)}
    
    def test_items_with_list_raises_error(self):
        """Test items() method with list data raises TypeError."""
        data = [{"id": 1}, {"id": 2}]
        fixture = JSONFixture(data)
        with pytest.raises(TypeError, match="Data is not a dictionary"):
            fixture.items()
    
    def test_get_with_dict(self):
        """Test get() method with dict data."""
        data = {"name": "John", "age": 30}
        fixture = JSONFixture(data)
        assert fixture.get("name") == "John"
        assert fixture.get("nonexistent") is None
        assert fixture.get("nonexistent", "default") == "default"
    
    def test_get_with_list_raises_error(self):
        """Test get() method with list data raises TypeError."""
        data = [{"id": 1}, {"id": 2}]
        fixture = JSONFixture(data)
        with pytest.raises(TypeError, match="Data is not a dictionary"):
            fixture.get("key")
    
    def test_length(self):
        """Test length() method."""
        dict_data = {"a": 1, "b": 2, "c": 3}
        list_data = [1, 2, 3, 4, 5]
        
        dict_fixture = JSONFixture(dict_data)
        list_fixture = JSONFixture(list_data)
        
        assert dict_fixture.length() == 3
        assert list_fixture.length() == 5
    
    def test_getitem_with_dict(self):
        """Test __getitem__ with dict data."""
        data = {"name": "John", "age": 30}
        fixture = JSONFixture(data)
        assert fixture["name"] == "John"
        assert fixture["age"] == 30
    
    def test_getitem_with_list(self):
        """Test __getitem__ with list data."""
        data = [{"id": 1}, {"id": 2}, {"id": 3}]
        fixture = JSONFixture(data)
        assert fixture[0] == {"id": 1}
        assert fixture[1] == {"id": 2}
        assert fixture[2] == {"id": 3}


class TestCSVFixture:
    """Test CSVFixture class."""
    
    def test_initialization(self):
        """Test CSVFixture initialization."""
        data = [
            {"name": "John", "age": "30"},
            {"name": "Jane", "age": "25"}
        ]
        fixture = CSVFixture(data)
        assert fixture.data == data
    
    def test_rows_property(self):
        """Test rows property."""
        data = [
            {"name": "John", "age": "30"},
            {"name": "Jane", "age": "25"}
        ]
        fixture = CSVFixture(data)
        assert fixture.rows == data
    
    def test_columns_property(self):
        """Test columns property."""
        data = [
            {"name": "John", "age": "30", "city": "NYC"},
            {"name": "Jane", "age": "25", "city": "LA"}
        ]
        fixture = CSVFixture(data)
        assert fixture.columns == ["name", "age", "city"]
    
    def test_columns_property_empty_data(self):
        """Test columns property with empty data."""
        fixture = CSVFixture([])
        assert fixture.columns == []
    
    def test_get_column(self):
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
    
    def test_get_column_missing_key(self):
        """Test get_column with missing key."""
        data = [
            {"name": "John", "age": "30"},
            {"name": "Jane"}  # Missing age
        ]
        fixture = CSVFixture(data)
        ages = fixture.get_column("age")
        assert ages == ["30", ""]
    
    def test_filter_rows(self):
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
    
    def test_filter_rows_no_matches(self):
        """Test filter_rows with no matches."""
        data = [
            {"name": "John", "age": "30"},
            {"name": "Jane", "age": "25"}
        ]
        fixture = CSVFixture(data)
        result = fixture.filter_rows(age="40")
        assert result == []
    
    def test_getitem(self):
        """Test __getitem__ method."""
        data = [
            {"name": "John", "age": "30"},
            {"name": "Jane", "age": "25"}
        ]
        fixture = CSVFixture(data)
        assert fixture[0] == {"name": "John", "age": "30"}
        assert fixture[1] == {"name": "Jane", "age": "25"}


class TestXMLFixture:
    """Test XMLFixture class."""
    
    def test_initialization(self):
        """Test XMLFixture initialization."""
        xml_string = "<root><item>test</item></root>"
        tree = etree.fromstring(xml_string)
        element_tree = etree.ElementTree(tree)
        
        fixture = XMLFixture(element_tree)
        assert fixture.data == element_tree
    
    def test_root_property(self):
        """Test root property."""
        xml_string = "<configuration><setting>value</setting></configuration>"
        tree = etree.fromstring(xml_string)
        element_tree = etree.ElementTree(tree)
        
        fixture = XMLFixture(element_tree)
        root = fixture.root
        assert root.tag == "configuration"
    
    def test_find_method(self):
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
    
    def test_findall_method(self):
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
    
    def test_xpath_method(self):
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
    
    def test_get_text_method(self):
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
