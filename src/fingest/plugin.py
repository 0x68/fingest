"""Fingest pytest plugin for data-driven fixtures."""

import csv
import json
import logging
import inspect
import functools
from pathlib import Path
from typing import Any, Dict
import pytest
from lxml import etree

# Global registry for data fixtures
_fixture_registry: Dict[str, Dict[str, Any]] = {}

# Registry for data loaders by file extension
_loader_registry: Dict[str, Any] = {}

# Logger for the plugin
logger = logging.getLogger(__name__)


class DataLoaderRegistry:
    """Registry for data loaders by file extension."""

    def __init__(self):
        self._loaders: Dict[str, Any] = {}
        self._register_default_loaders()

    def _register_default_loaders(self):
        """Register default loaders for common file types."""
        self.register("json", self._load_json)
        self.register("csv", self._load_csv)
        self.register("xml", self._load_xml)

    def register(self, extension: str, loader):
        """Register a loader for a file extension.

        Args:
            extension: File extension (without dot).
            loader: Function that takes a Path and returns loaded data.
        """
        self._loaders[extension.lower()] = loader
        logger.debug(f"Registered loader for .{extension} files")

    def get_loader(self, extension: str):
        """Get a loader for a file extension.

        Args:
            extension: File extension (without dot).

        Returns:
            Loader function or None if not found.
        """
        return self._loaders.get(extension.lower())

    def load_data(self, path: Path) -> Any:
        """Load data from a file using the appropriate loader.

        Args:
            path: Path to the data file.

        Returns:
            Loaded data.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the file format is unsupported or data is invalid.
        """
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")

        extension = path.suffix[1:].lower()
        loader = self.get_loader(extension)

        if not loader:
            raise ValueError(f"Unsupported file format: {extension}")

        try:
            return loader(path)
        except Exception as e:
            raise ValueError(f"Failed to load {path}: {e}") from e

    @staticmethod
    def _load_json(path: Path) -> Any:
        """Load JSON data from file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file {path}: {e}") from e
        except UnicodeDecodeError as e:
            raise ValueError(f"Cannot decode JSON file {path}: {e}") from e

    @staticmethod
    def _load_csv(path: Path) -> Any:
        """Load CSV data from file."""
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader)
        except UnicodeDecodeError as e:
            raise ValueError(f"Cannot decode CSV file {path}: {e}") from e

    @staticmethod
    def _load_xml(path: Path) -> Any:
        """Load XML data from file."""
        try:
            return etree.parse(str(path))
        except etree.XMLSyntaxError as e:
            raise ValueError(f"Invalid XML in file {path}: {e}") from e


# Global data loader registry
_data_loader_registry = DataLoaderRegistry()


def pytest_addoption(parser):
    parser.addini(
        name="fingest_fixture_path",
        help="Base path for fixture data files",
        default="data",
    )


def pytest_configure(config):
    data_path = config.getini("fingest_fixture_path")
    config.fingest_fixture_path = data_path


def data_fixture(file_path: str, description: str = "", loader=None):
    """Decorator to register a class or function as a data-backed fixture.

    Args:
        file_path: Path to the data file (relative to fingest_fixture_path).
        description: Optional description for debugging and documentation.
        loader: Optional custom data loader function.

    Returns:
        The decorated class or function.

    Example:
        @data_fixture("users.json", description="Test user data")
        class UserData(JSONFixture):
            pass

        @data_fixture("config.yaml", loader=custom_yaml_loader)
        def config_data(data):
            return data
    """
    def wrapper(obj):
        _fixture_registry[obj.__name__] = {
            "obj": obj,
            "path": Path(file_path),
            "description": description,
            "is_class": isinstance(obj, type),
            "loader": loader
        }
        logger.debug(f"Registered data fixture: {obj.__name__} -> {file_path}")
        return obj

    return wrapper


def register_loader(extension: str, loader):
    """Register a custom data loader for a file extension.

    Args:
        extension: File extension (without dot).
        loader: Function that takes a Path and returns loaded data.

    Example:
        def yaml_loader(path):
            import yaml
            with open(path) as f:
                return yaml.safe_load(f)

        register_loader("yaml", yaml_loader)
    """
    _data_loader_registry.register(extension, loader)


def _load_data(path: Path) -> Any:
    """Load data from a file using the global data loader registry.

    Args:
        path: Path to the data file.

    Returns:
        Loaded data.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file format is unsupported or data is invalid.
    """
    return _data_loader_registry.load_data(path)


class FixtureWrapper:
    """Wrapper for fixture instances that adds description and delegates all operations."""

    def __init__(self, instance, description: str):
        self._instance = instance
        self._description = description

    def __getattr__(self, item):
        """Delegate attribute access to the wrapped instance."""
        return getattr(self._instance, item)

    def __getitem__(self, key):
        """Delegate indexing to the wrapped instance."""
        return self._instance[key]

    def __len__(self):
        """Delegate len() to the wrapped instance."""
        return len(self._instance)

    def __bool__(self):
        """Delegate bool() to the wrapped instance."""
        return bool(self._instance)

    def __iter__(self):
        """Delegate iteration to the wrapped instance."""
        return iter(self._instance)

    def __repr__(self):
        """Return the description as representation."""
        return f"{self._description}"

    def __str__(self):
        """Return a detailed string representation."""
        return f"{self._instance}  (Fixture description: {self._description})"


def pytest_sessionstart(session):
    """Generate real fixtures at test session start."""
    data_root = getattr(session.config, "fingest_fixture_path", "data")

    for name, info in _fixture_registry.items():
        obj = info["obj"]
        path = Path(data_root) / Path(info["path"])
        desc = info["description"]
        custom_loader = info.get("loader")

        def create_fixture(obj=obj, path=path, desc=desc, loader=custom_loader):
            # Check if obj is a function and preserve its signature
            if callable(obj) and not isinstance(obj, type):
                # Get the original function's signature and parameters
                sig = inspect.signature(obj)
                params = list(sig.parameters.values())

                # Create a new signature that excludes the first 'data' parameter
                # but keeps all other parameters (fixture dependencies)
                if params and params[0].name in ['data', 'self']:
                    new_params = params[1:]  # Skip the first parameter (data)
                else:
                    new_params = params

                new_sig = sig.replace(parameters=new_params)

                # Create a wrapper function that has the correct signature for pytest
                def create_wrapper():
                    def wrapper(*args, **kwargs):
                        try:
                            # Use custom loader if provided, otherwise use default
                            if loader:
                                data = loader(path)
                            else:
                                data = _load_data(path)

                            # Call the original function with data as first argument,
                            # followed by any fixture dependencies
                            result = obj(data, *args, **kwargs)

                            return FixtureWrapper(result, desc)
                        except Exception as e:
                            logger.error(f"Failed to create fixture {name}: {e}")
                            raise

                    # Set the signature to match the original function minus the data parameter
                    wrapper.__signature__ = new_sig
                    # Preserve other function attributes
                    wrapper.__name__ = obj.__name__
                    wrapper.__doc__ = obj.__doc__
                    wrapper.__module__ = obj.__module__

                    return wrapper

                # Create the wrapper and apply the pytest.fixture decorator
                wrapper_func = create_wrapper()
                return pytest.fixture(name=name)(wrapper_func)
            else:
                # For classes, keep the original behavior
                @pytest.fixture(name=name)
                def _fixture():
                    try:
                        # Use custom loader if provided, otherwise use default
                        if loader:
                            data = loader(path)
                        else:
                            data = _load_data(path)

                        # Both classes and functions are called with data
                        result = obj(data)

                        return FixtureWrapper(result, desc)
                    except Exception as e:
                        logger.error(f"Failed to create fixture {name}: {e}")
                        raise
                return _fixture

        # Register the fixture in pytest's fixture registry
        fixture_func = create_fixture()
        globals()[name] = fixture_func
