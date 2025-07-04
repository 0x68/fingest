"""Tests for fingest plugin functionality."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from fingest.plugin import (
    data_fixture, 
    _load_data, 
    register_loader,
    DataLoaderRegistry,
    _data_loader_registry,
    _fixture_registry
)
from fingest.types import BaseFixture


class TestDataLoaderRegistry:
    """Test the DataLoaderRegistry class."""
    
    def test_registry_initialization(self):
        """Test that registry initializes with default loaders."""
        registry = DataLoaderRegistry()
        
        # Check that default loaders are registered
        assert registry.get_loader("json") is not None
        assert registry.get_loader("csv") is not None
        assert registry.get_loader("xml") is not None
    
    def test_register_custom_loader(self):
        """Test registering a custom loader."""
        registry = DataLoaderRegistry()
        
        def custom_loader(path):
            return {"custom": "data"}
        
        registry.register("custom", custom_loader)
        assert registry.get_loader("custom") == custom_loader
    
    def test_get_nonexistent_loader(self):
        """Test getting a loader for unsupported extension."""
        registry = DataLoaderRegistry()
        assert registry.get_loader("unsupported") is None
    
    def test_case_insensitive_extension(self):
        """Test that extensions are case insensitive."""
        registry = DataLoaderRegistry()
        
        def custom_loader(path):
            return {"test": "data"}
        
        registry.register("TXT", custom_loader)
        assert registry.get_loader("txt") == custom_loader
        assert registry.get_loader("TXT") == custom_loader


class TestDataLoading:
    """Test data loading functionality."""
    
    def test_load_json_data(self):
        """Test loading JSON data."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"test": "data"}, f)
            temp_path = Path(f.name)
        
        try:
            data = _load_data(temp_path)
            assert data == {"test": "data"}
        finally:
            temp_path.unlink()
    
    def test_load_csv_data(self):
        """Test loading CSV data."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,age\nJohn,30\nJane,25\n")
            temp_path = Path(f.name)
        
        try:
            data = _load_data(temp_path)
            assert len(data) == 2
            assert data[0] == {"name": "John", "age": "30"}
            assert data[1] == {"name": "Jane", "age": "25"}
        finally:
            temp_path.unlink()
    
    def test_load_xml_data(self):
        """Test loading XML data."""
        xml_content = '<?xml version="1.0"?><root><item>test</item></root>'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = Path(f.name)
        
        try:
            data = _load_data(temp_path)
            assert data.getroot().tag == "root"
            assert data.getroot().find("item").text == "test"
        finally:
            temp_path.unlink()
    
    def test_load_nonexistent_file(self):
        """Test loading a file that doesn't exist."""
        nonexistent_path = Path("/nonexistent/file.json")
        with pytest.raises(FileNotFoundError, match="Data file not found"):
            _load_data(nonexistent_path)
    
    def test_load_unsupported_format(self):
        """Test loading an unsupported file format."""
        with tempfile.NamedTemporaryFile(suffix='.unsupported', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                _load_data(temp_path)
        finally:
            temp_path.unlink()
    
    def test_load_invalid_json(self):
        """Test loading invalid JSON data."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json}')  # Invalid JSON
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                _load_data(temp_path)
        finally:
            temp_path.unlink()
    
    def test_load_invalid_xml(self):
        """Test loading invalid XML data."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write('<invalid><unclosed>')  # Invalid XML
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Invalid XML"):
                _load_data(temp_path)
        finally:
            temp_path.unlink()


class TestDataFixtureDecorator:
    """Test the data_fixture decorator."""
    
    def test_register_class_fixture(self):
        """Test registering a class-based fixture."""
        initial_count = len(_fixture_registry)
        
        @data_fixture("test.json", description="Test fixture")
        class TestFixture(BaseFixture):
            pass
        
        assert len(_fixture_registry) == initial_count + 1
        assert "TestFixture" in _fixture_registry
        
        fixture_info = _fixture_registry["TestFixture"]
        assert fixture_info["obj"] == TestFixture
        assert fixture_info["path"] == Path("test.json")
        assert fixture_info["description"] == "Test fixture"
        assert fixture_info["is_class"] is True
    
    def test_register_function_fixture(self):
        """Test registering a function-based fixture."""
        initial_count = len(_fixture_registry)
        
        @data_fixture("test.json", description="Test function")
        def test_function(data):
            return data
        
        assert len(_fixture_registry) == initial_count + 1
        assert "test_function" in _fixture_registry
        
        fixture_info = _fixture_registry["test_function"]
        assert fixture_info["obj"] == test_function
        assert fixture_info["path"] == Path("test.json")
        assert fixture_info["description"] == "Test function"
        assert fixture_info["is_class"] is False
    
    def test_register_fixture_with_custom_loader(self):
        """Test registering a fixture with custom loader."""
        def custom_loader(path):
            return {"custom": "data"}
        
        initial_count = len(_fixture_registry)
        
        @data_fixture("test.custom", loader=custom_loader)
        class CustomFixture(BaseFixture):
            pass
        
        assert len(_fixture_registry) == initial_count + 1
        fixture_info = _fixture_registry["CustomFixture"]
        assert fixture_info["loader"] == custom_loader


class TestRegisterLoader:
    """Test the register_loader function."""
    
    def test_register_global_loader(self):
        """Test registering a loader globally."""
        def yaml_loader(path):
            return {"yaml": "data"}
        
        register_loader("yaml", yaml_loader)
        assert _data_loader_registry.get_loader("yaml") == yaml_loader
    
    def test_use_registered_loader(self):
        """Test using a registered loader."""
        def txt_loader(path):
            with open(path, 'r') as f:
                return f.read().strip()
        
        register_loader("txt", txt_loader)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello, World!")
            temp_path = Path(f.name)
        
        try:
            data = _load_data(temp_path)
            assert data == "Hello, World!"
        finally:
            temp_path.unlink()


class TestErrorHandling:
    """Test error handling in various scenarios."""
    
    def test_directory_instead_of_file(self):
        """Test error when path points to directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dir_path = Path(temp_dir)
            with pytest.raises(ValueError, match="Path is not a file"):
                _load_data(dir_path)
    
    def test_permission_error(self):
        """Test handling of permission errors."""
        # This test might be platform-specific
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            # Make file unreadable (Unix-like systems)
            temp_path.chmod(0o000)
            
            # This might raise PermissionError or ValueError depending on the system
            with pytest.raises((PermissionError, ValueError)):
                _load_data(temp_path)
        finally:
            # Restore permissions and clean up
            temp_path.chmod(0o644)
            temp_path.unlink()


class TestPytestIntegration:
    """Test pytest integration functionality."""
    
    def test_pytest_addoption(self):
        """Test that pytest options are added correctly."""
        from fingest.plugin import pytest_addoption
        
        # Mock parser
        parser = MagicMock()
        pytest_addoption(parser)
        
        # Verify addini was called with correct parameters
        parser.addini.assert_called_once_with(
            name="fingest_fixture_path",
            help="Base path for fixture data files",
            default="data"
        )
    
    def test_pytest_configure(self):
        """Test pytest configuration."""
        from fingest.plugin import pytest_configure
        
        # Mock config
        config = MagicMock()
        config.getini.return_value = "test_data"
        
        pytest_configure(config)
        
        # Verify configuration was set
        config.getini.assert_called_once_with("fingest_fixture_path")
        assert config.fingest_fixture_path == "test_data"
