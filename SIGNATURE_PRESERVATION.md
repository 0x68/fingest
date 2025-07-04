# Fixture Signature Preservation in Fingest

## Overview

Fingest now preserves the original function signatures when creating fixtures from function-based data fixtures. This means that function fixtures can depend on other pytest fixtures, and pytest's dependency injection system will work correctly.

## How It Works

When you define a function-based fixture with `@data_fixture`, Fingest:

1. **Inspects the original function signature** to identify parameters
2. **Removes the first `data` parameter** (which is injected by Fingest)
3. **Preserves all other parameters** as pytest fixture dependencies
4. **Creates a wrapper function** with the correct signature for pytest
5. **Handles dependency injection** seamlessly

## Examples

### Basic Function Fixture with Dependencies

```python
import pytest
from fingest import data_fixture

@pytest.fixture
def database_config():
    return {"host": "localhost", "port": 5432}

@data_fixture("users.json", description="User data with database config")
def user_data_with_config(data, database_config):
    """Function fixture that depends on other fixtures."""
    return {
        "users": data,
        "db_config": database_config,
        "total_users": len(data)
    }

def test_user_data(user_data_with_config):
    assert user_data_with_config["users"] is not None
    assert user_data_with_config["db_config"]["host"] == "localhost"
```

### Function Fixture with Optional Parameters

```python
@data_fixture("config.json", description="Config with optional settings")
def config_with_options(data, database_config, timeout=30, debug=False):
    """Function fixture with optional parameters."""
    return {
        "config": data,
        "db_config": database_config,
        "timeout": timeout,
        "debug": debug
    }
```

### Function Fixture with Complex Signature

```python
@data_fixture("data.json", description="Complex signature fixture")
def complex_fixture(data, required_dep, optional_dep="default", *args, **kwargs):
    """Function fixture with complex signature including *args and **kwargs."""
    return {
        "data": data,
        "required": required_dep,
        "optional": optional_dep,
        "args": args,
        "kwargs": kwargs
    }
```

## Benefits

1. **Seamless Integration**: Function fixtures work exactly like regular pytest fixtures
2. **Dependency Injection**: Can depend on other fixtures, including built-in ones like `tmp_path`, `monkeypatch`, etc.
3. **Optional Parameters**: Support for default values and optional parameters
4. **Complex Signatures**: Support for `*args` and `**kwargs`
5. **Type Safety**: Original type hints and signatures are preserved
6. **IDE Support**: IDEs can properly understand fixture dependencies

## Technical Details

### Signature Transformation

Original function:
```python
def my_fixture(data, dep1, dep2="default"):
    return process(data, dep1, dep2)
```

Generated pytest fixture signature:
```python
def my_fixture(dep1, dep2="default"):  # 'data' parameter removed
    # Fingest loads data and calls original function
    return process(data, dep1, dep2)
```

### Error Handling

If a function fixture has dependencies that don't exist, pytest will provide clear error messages:

```
fixture 'missing_dependency' not found
available fixtures: [list of available fixtures]
```

### Backward Compatibility

- **Class-based fixtures**: Unchanged behavior, no signature preservation needed
- **Simple function fixtures**: Work exactly as before
- **Function fixtures without dependencies**: Work exactly as before

## Migration Guide

No migration is needed! Existing fixtures continue to work exactly as before. The signature preservation feature is automatically applied to function-based fixtures that have dependencies.

### Before (Limited)
```python
@data_fixture("data.json")
def my_fixture(data):
    # Could only use the data, no other fixtures
    return process(data)
```

### After (Enhanced)
```python
@data_fixture("data.json")
def my_fixture(data, other_fixture, optional_param="default"):
    # Can now depend on other fixtures!
    return process(data, other_fixture, optional_param)
```

## Testing

The signature preservation feature is thoroughly tested with:

- Unit tests for signature inspection and transformation
- Integration tests with real pytest fixtures
- Tests for complex signatures with `*args` and `**kwargs`
- Tests for optional parameters and default values
- Error handling tests

Run the tests:
```bash
pytest tests/test_signature_preservation.py -v
pytest tests/test_integration_signature.py -v
```

## Implementation Notes

The implementation uses Python's `inspect` module to:
- Extract the original function signature
- Create a new signature without the `data` parameter
- Preserve parameter types, defaults, and annotations
- Handle special parameter types (`*args`, `**kwargs`)

The generated wrapper function maintains all the original function's metadata while providing the correct interface for pytest's dependency injection system.
