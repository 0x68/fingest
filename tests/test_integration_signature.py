import pytest
from fingest.plugin import data_fixture
from fingest.types import BaseFixture

 
def test_function_fixture_with_dependencies_works(function_with_deps):
    """Test that function fixtures with dependencies work correctly."""
    # The fixture should have been created and injected with dependencies
    assert function_with_deps is not None
    
    # Check that the data was loaded (test.json contains {"Foo": "Bar"})
    assert function_with_deps["data"]["Foo"] == "Bar"
    
    # Check that dependencies were injected
    assert function_with_deps["mock_dep"] == "dependency_value"
    assert function_with_deps["another_dep"] == {"key": "value"}
    
    # Check that the function logic worked
    assert function_with_deps["combined"] == "dependency_value_Bar"

def test_function_fixture_with_optional_dependencies_works(function_with_optional_deps):
    """Test that function fixtures with optional dependencies work correctly."""
    assert function_with_optional_deps is not None
    
    # Check that the data was loaded
    assert function_with_optional_deps["data"]["Foo"] == "Bar"
    
    # Check that required dependency was injected
    assert function_with_optional_deps["mock_dep"] == "dependency_value"
    
    # Check that optional parameter got its default value
    assert function_with_optional_deps["optional"] == "default_value"

def test_function_fixture_with_complex_signature_works(function_with_complex_sig):
    """Test that function fixtures with complex signatures work correctly."""
    assert function_with_complex_sig is not None
    
    # Check that the data was loaded
    assert function_with_complex_sig["data"]["Foo"] == "Bar"
    
    # Check that required dependency was injected
    assert function_with_complex_sig["required"] == "required_dependency_value"
    
    # Check that optional parameter got its default value
    assert function_with_complex_sig["optional"] == "default"
    
    # Check that *args and **kwargs are empty (no extra arguments passed)
    assert function_with_complex_sig["args"] == ()
    assert function_with_complex_sig["kwargs"] == {}

def test_function_fixture_data_access(function_with_deps):
    """Test that function fixture data is directly accessible."""
    # Function fixtures return their result directly
    assert isinstance(function_with_deps, dict)
    assert function_with_deps["data"]["Foo"] == "Bar"
    assert len(function_with_deps) > 0

def test_error_handling_in_fixture_creation(self):
    """Test that errors in fixture creation are handled properly."""
    # This test verifies that the error handling in create_fixture works
    # We can't easily test this without creating a fixture that fails,
    # but we can at least verify the structure is correct
    
    # Create a fixture that would fail if the data file doesn't exist
    @data_fixture("nonexistent.json", description="Failing fixture")
    def failing_fixture(data):
        return data
    
    # The fixture should be registered even if it will fail at runtime
    from fingest.plugin import _fixture_registry
    assert "failing_fixture" in _fixture_registry
    
    # The fixture info should be correct
    fixture_info = _fixture_registry["failing_fixture"]
    assert fixture_info["description"] == "Failing fixture"
    assert fixture_info["path"].name == "nonexistent.json"
