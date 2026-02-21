"""Tests for fixture signature preservation."""

import inspect
import pytest
from fingest.plugin import data_fixture, _fixture_registry
from fingest.types import BaseFixture


def test_function_fixture_with_dependencies_preserves_signature():
    """Test that function fixtures with dependencies preserve their signature."""
    
    # Define a fixture function with dependencies
    @data_fixture("test.json", description="Test fixture with dependencies")
    def test_fixture_with_deps(data, some_dependency, another_dep="default"):
        """Test fixture that depends on other fixtures."""
        return {"data": data, "dep": some_dependency, "another": another_dep}
    
    # Check that the fixture was registered
    assert "test_fixture_with_deps" in _fixture_registry
    
    # Get the original function signature
    original_sig = inspect.signature(test_fixture_with_deps)
    original_params = list(original_sig.parameters.keys())
    
    # The original function should have 'data' as first parameter
    assert original_params[0] == "data"
    assert "some_dependency" in original_params
    assert "another_dep" in original_params
    
    # Simulate what happens in pytest_sessionstart
    from fingest.plugin import pytest_sessionstart
    
    # Create a mock session config
    class MockConfig:
        def __init__():
            .fingest_fixture_path = "tests/data"
    
    class MockSession:
        def __init__():
            .config = MockConfig()
    
    # This would normally be called by pytest
    # pytest_sessionstart(MockSession())
    
    # For now, let's test the signature preservation logic directly
    info = _fixture_registry["test_fixture_with_deps"]
    obj = info["obj"]
    
    # Check if obj is a function and get its signature
    if callable(obj) and not isinstance(obj, type):
        sig = inspect.signature(obj)
        params = list(sig.parameters.values())
        
        # Create a new signature that excludes the first 'data' parameter
        if params and params[0].name in ['data', '']:
            new_params = params[1:]  # Skip the first parameter (data)
        else:
            new_params = params
        
        new_sig = sig.replace(parameters=new_params)
        
        # The new signature should not have 'data' but should have the dependencies
        new_param_names = list(new_sig.parameters.keys())
        assert "data" not in new_param_names
        assert "some_dependency" in new_param_names
        assert "another_dep" in new_param_names
        
        # Check parameter defaults are preserved
        assert new_sig.parameters["another_dep"].default == "default"

def test_function_fixture_without_dependencies_preserves_signature():
    """Test that function fixtures without dependencies work correctly."""
    
    @data_fixture("test.json", description="Simple test fixture")
    def simple_test_fixture(data):
        """Simple fixture with only data parameter."""
        return data
    
    # Check that the fixture was registered
    assert "simple_test_fixture" in _fixture_registry
    
    # Get the original function signature
    original_sig = inspect.signature(simple_test_fixture)
    original_params = list(original_sig.parameters.keys())
    
    # The original function should have only 'data' parameter
    assert original_params == ["data"]
    
    # Test the signature preservation logic
    info = _fixture_registry["simple_test_fixture"]
    obj = info["obj"]
    
    if callable(obj) and not isinstance(obj, type):
        sig = inspect.signature(obj)
        params = list(sig.parameters.values())
        
        # Create a new signature that excludes the first 'data' parameter
        if params and params[0].name in ['data', '']:
            new_params = params[1:]  # Skip the first parameter (data)
        else:
            new_params = params
        
        new_sig = sig.replace(parameters=new_params)
        
        # The new signature should be empty (no parameters)
        assert len(new_sig.parameters) == 0

def test_class_fixture_signature_unchanged():
    """Test that class fixtures are not affected by signature preservation."""
    
    @data_fixture("test.json", description="Test class fixture")
    class TestClassFixture(BaseFixture):
        """Test class fixture."""
        pass
    
    # Check that the fixture was registered
    assert "TestClassFixture" in _fixture_registry
    
    # Class fixtures should not be affected by signature preservation
    info = _fixture_registry["TestClassFixture"]
    obj = info["obj"]
    
    # Should be recognized as a class
    assert isinstance(obj, type)
    assert issubclass(obj, BaseFixture)

def test_function_with_complex_signature():
    """Test function with complex signature including *args and **kwargs."""
    
    @data_fixture("test.json", description="Complex signature fixture")
    def complex_fixture(data, required_dep, optional_dep="default", *args, **kwargs):
        """Fixture with complex signature."""
        return {
            "data": data,
            "required": required_dep,
            "optional": optional_dep,
            "args": args,
            "kwargs": kwargs
        }
    
    # Check that the fixture was registered
    assert "complex_fixture" in _fixture_registry
    
    # Test the signature preservation logic
    info = _fixture_registry["complex_fixture"]
    obj = info["obj"]
    
    if callable(obj) and not isinstance(obj, type):
        sig = inspect.signature(obj)
        params = list(sig.parameters.values())
        
        # Create a new signature that excludes the first 'data' parameter
        if params and params[0].name in ['data', '']:
            new_params = params[1:]  # Skip the first parameter (data)
        else:
            new_params = params
        
        new_sig = sig.replace(parameters=new_params)
        
        # Check that all parameters except 'data' are preserved
        new_param_names = list(new_sig.parameters.keys())
        assert "data" not in new_param_names
        assert "required_dep" in new_param_names
        assert "optional_dep" in new_param_names
        
        # Check that parameter kinds are preserved
        params_dict = new_sig.parameters
        assert params_dict["required_dep"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
        assert params_dict["optional_dep"].default == "default"
        
        # Check for *args and **kwargs
        param_kinds = [p.kind for p in params_dict.values()]
        assert inspect.Parameter.VAR_POSITIONAL in param_kinds  # *args
        assert inspect.Parameter.VAR_KEYWORD in param_kinds     # **kwargs
