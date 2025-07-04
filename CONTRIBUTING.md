# Contributing to Fingest

Thank you for your interest in contributing to Fingest! This document provides guidelines and information for contributors.

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/fingest.git
   cd fingest
   ```
3. **Set up development environment**:
   ```bash
   make dev-install
   ```
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
5. **Make your changes** and ensure tests pass:
   ```bash
   make check-all
   ```
6. **Commit and push** your changes
7. **Create a Pull Request** on GitHub

## 🛠️ Development Setup

### Prerequisites

- Python 3.11 or higher
- Poetry (for dependency management)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/0x68/fingest.git
cd fingest

# Install dependencies and development tools
make dev-install

# Verify installation
make test
```

### Development Workflow

```bash
# Run all checks before committing
make check-all

# Or run individual checks
make lint          # Code linting
make type-check    # Type checking
make test          # Run tests
make format        # Format code

# Run tests with coverage
make test-cov
```

## 📝 Code Style

We use several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pre-commit**: Git hooks for quality checks

### Formatting

```bash
# Format all code
make format

# Check formatting without changing files
poetry run black --check src tests
poetry run isort --check-only src tests
```

### Type Hints

- All public functions and methods should have type hints
- Use `typing` module for complex types
- Tests can have relaxed type checking

## 🧪 Testing

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
poetry run pytest tests/test_plugin.py

# Run with verbose output
make test-verbose
```

### Writing Tests

- Place tests in the `tests/` directory
- Use descriptive test names: `test_should_load_json_data_when_file_exists`
- Group related tests in classes
- Use pytest fixtures for test data
- Test both success and error cases

Example test structure:
```python
class TestDataLoading:
    """Test data loading functionality."""
    
    def test_should_load_json_data_when_file_exists(self):
        """Test that JSON data loads correctly from existing file."""
        # Arrange
        # Act
        # Assert
        
    def test_should_raise_error_when_file_not_found(self):
        """Test that appropriate error is raised for missing file."""
        # Arrange
        # Act & Assert
        with pytest.raises(FileNotFoundError):
            # Test code
```

## 📚 Documentation

### Docstrings

Use Google-style docstrings:

```python
def load_data(path: Path, format: str) -> Any:
    """Load data from a file.
    
    Args:
        path: Path to the data file.
        format: Expected file format (json, csv, xml).
        
    Returns:
        Loaded data in appropriate format.
        
    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file format is unsupported.
        
    Example:
        >>> data = load_data(Path("users.json"), "json")
        >>> print(data[0]["name"])
        "Alice"
    """
```

### README Updates

When adding new features:
1. Update the feature list
2. Add usage examples
3. Update the API reference if needed
4. Consider adding to the changelog

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Python version** and operating system
2. **Fingest version**
3. **Minimal code example** that reproduces the issue
4. **Expected behavior** vs **actual behavior**
5. **Error messages** and stack traces
6. **Data files** used (if applicable)

## ✨ Feature Requests

For new features:

1. **Check existing issues** to avoid duplicates
2. **Describe the use case** and motivation
3. **Provide examples** of how the feature would be used
4. **Consider backwards compatibility**

## 🔄 Pull Request Process

### Before Submitting

1. **Run all checks**: `make check-all`
2. **Update tests** for new functionality
3. **Update documentation** if needed
4. **Add changelog entry** for significant changes

### PR Guidelines

- **Clear title** describing the change
- **Detailed description** of what and why
- **Link to related issues**
- **Screenshots** for UI changes (if applicable)
- **Breaking changes** clearly marked

### Review Process

1. **Automated checks** must pass (CI/CD)
2. **Code review** by maintainers
3. **Testing** on different environments
4. **Documentation review**
5. **Merge** when approved

## 🏗️ Architecture

### Project Structure

```
fingest/
├── src/fingest/           # Main package
│   ├── __init__.py       # Package exports
│   ├── plugin.py         # Pytest plugin implementation
│   └── types.py          # Fixture base classes
├── tests/                # Test suite
│   ├── conftest.py       # Test fixtures
│   ├── data/             # Test data files
│   ├── test_plugin.py    # Plugin tests
│   ├── test_types.py     # Type tests
│   └── test_fixtures.py  # Integration tests
├── pyproject.toml        # Project configuration
└── README.md             # Documentation
```

### Key Components

1. **Plugin System**: `plugin.py` implements pytest hooks
2. **Data Loaders**: Registry-based system for file formats
3. **Fixture Types**: Specialized classes for different data formats
4. **Wrapper System**: Transparent delegation with descriptions

## 🎯 Coding Guidelines

### General Principles

- **Simplicity**: Prefer simple, readable solutions
- **Consistency**: Follow existing patterns
- **Documentation**: Code should be self-documenting
- **Testing**: All code should be tested
- **Backwards Compatibility**: Avoid breaking changes

### Specific Guidelines

- **Function length**: Keep functions under 50 lines
- **Class design**: Single responsibility principle
- **Error handling**: Provide clear, actionable error messages
- **Performance**: Optimize for common use cases
- **Dependencies**: Minimize external dependencies

## 📋 Release Process

1. **Update version** in `pyproject.toml`
2. **Update changelog** in `README.md`
3. **Run full test suite**: `make ci`
4. **Create release tag**: `git tag v0.1.0`
5. **Build package**: `make build`
6. **Publish to PyPI**: `make publish`

## 🤝 Community

- **Be respectful** and inclusive
- **Help others** learn and contribute
- **Share knowledge** and best practices
- **Provide constructive feedback**

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Email**: tim@0x68.de for private matters

Thank you for contributing to Fingest! 🎉
