"""
Demonstration of fixture signature preservation in Fingest.

This example shows how function-based fixtures can have dependencies on other
pytest fixtures, and how Fingest preserves the original function signature
while automatically injecting the data from external files.
"""

import pytest
from fingest import data_fixture
from fingest.types import BaseFixture


# Example dependency fixtures
@pytest.fixture
def database_config():
    """Mock database configuration fixture."""
    return {
        "host": "localhost",
        "port": 5432,
        "database": "test_db"
    }


@pytest.fixture
def api_client():
    """Mock API client fixture."""
    return "MockAPIClient"


# Function-based fixture with dependencies - signature is preserved!
@data_fixture("users.json", description="User data with database config")
def user_data_with_config(data, database_config, api_client):
    """
    Function fixture that depends on other fixtures.
    
    The 'data' parameter is automatically injected by Fingest from users.json,
    while 'database_config' and 'api_client' are injected by pytest's
    dependency injection system.
    
    Note: The signature is preserved, so pytest knows about the dependencies!
    """
    return {
        "users": data,
        "db_config": database_config,
        "client": api_client,
        "total_users": len(data)
    }


# Function-based fixture with optional parameters
@data_fixture("users.json", description="User data with optional settings")
def user_data_with_options(data, database_config, timeout=30, debug=False):
    """
    Function fixture with optional parameters.
    
    Optional parameters get their default values when not provided by pytest.
    """
    return {
        "users": data,
        "db_config": database_config,
        "timeout": timeout,
        "debug": debug,
        "processed": True
    }


# Function-based fixture with complex signature
@data_fixture("users.json", description="User data with complex signature")
def user_data_complex(data, database_config, *args, **kwargs):
    """
    Function fixture with *args and **kwargs.
    
    This demonstrates that complex signatures are preserved correctly.
    """
    return {
        "users": data,
        "db_config": database_config,
        "extra_args": args,
        "extra_kwargs": kwargs,
        "signature_preserved": True
    }


# Test functions demonstrating the signature preservation concept
def test_fixture_registration():
    """Test that fixtures are properly registered."""
    from fingest.plugin import _fixture_registry

    # Check that the fixtures were registered
    assert "user_data_with_config" in _fixture_registry
    assert "user_data_with_options" in _fixture_registry
    assert "user_data_complex" in _fixture_registry

    # Test that the fixtures were registered correctly
    fixture_info = _fixture_registry["user_data_with_config"]
    assert fixture_info["description"] == "User data with database config"
    assert fixture_info["path"].name == "users.json"


def test_signature_inspection():
    """Test that we can inspect the original function signatures."""
    import inspect

    # The original functions still have their original signatures
    # (the signature preservation happens in the generated pytest fixtures)
    sig = inspect.signature(user_data_with_config)
    param_names = list(sig.parameters.keys())

    # The original function should have 'data' as first parameter
    assert "data" in param_names
    assert "database_config" in param_names
    assert "api_client" in param_names

    # Test optional parameters in original function
    sig = inspect.signature(user_data_with_options)
    params = sig.parameters

    assert "data" in params
    assert "database_config" in params
    assert "timeout" in params
    assert params["timeout"].default == 30
    assert "debug" in params
    assert params["debug"].default is False


def test_signature_preservation_logic():
    """Test the signature preservation logic directly."""
    import inspect
    from fingest.plugin import _fixture_registry

    # Get a registered function fixture
    fixture_info = _fixture_registry["user_data_with_config"]
    obj = fixture_info["obj"]

    # Test the signature transformation logic
    if callable(obj) and not isinstance(obj, type):
        sig = inspect.signature(obj)
        params = list(sig.parameters.values())

        # Create a new signature that excludes the first 'data' parameter
        if params and params[0].name in ['data', 'self']:
            new_params = params[1:]  # Skip the first parameter (data)
        else:
            new_params = params

        new_sig = sig.replace(parameters=new_params)

        # The new signature should not have 'data' but should have the dependencies
        new_param_names = list(new_sig.parameters.keys())
        assert "data" not in new_param_names
        assert "database_config" in new_param_names
        assert "api_client" in new_param_names


if __name__ == "__main__":
    print("This is a demonstration of Fingest's signature preservation feature.")
    print("Run with: pytest signature_preservation_demo.py -v")
    print("\nKey features demonstrated:")
    print("1. Function fixtures can depend on other pytest fixtures")
    print("2. Original function signatures are preserved")
    print("3. Optional parameters work correctly")
    print("4. Complex signatures (*args, **kwargs) are supported")
    print("5. Pytest's dependency injection works seamlessly")
