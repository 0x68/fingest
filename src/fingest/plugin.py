"""Fingest pytest plugin for data-driven fixtures."""

import csv
import inspect
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from lxml import etree

# Global registry for data fixtures
_fixture_registry: dict[str, dict[str, Any]] = {}

# Logger for the plugin
logger = logging.getLogger(__name__)


class DataLoaderRegistry:
    """Registry for data loaders by file extension."""

    def __init__(self) -> None:
        self._loaders: dict[str, Callable[[Path], Any]] = {}
        self._register_default_loaders()

    def _register_default_loaders(self) -> None:
        """Register default loaders for common file types."""
        self.register("json", self._load_json)
        self.register("csv", self._load_csv)
        self.register("xml", self._load_xml)

    def register(self, extension: str, loader: Callable[[Path], Any]) -> None:
        """Register a loader for a file extension.

        Args:
            extension: File extension (without dot).
            loader: Function that takes a Path and returns loaded data.
        """
        self._loaders[extension.lower()] = loader
        logger.debug(f"Registered loader for .{extension} files")

    def __repr__(self) -> str:
        """Return a debug-friendly representation."""
        exts = ", ".join(sorted(self._loaders.keys()))
        return f"DataLoaderRegistry(loaders=[{exts}])"

    def get_loader(self, extension: str) -> Callable[[Path], Any] | None:
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
            with open(path, encoding="utf-8") as f:
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


def pytest_addoption(parser: Any) -> None:
    parser.addini(
        name="fingest_fixture_path",
        help="Base path for fixture data files",
        default="data",
    )


def pytest_configure(config: Any) -> None:
    data_path = config.getini("fingest_fixture_path")
    config.fingest_fixture_path = data_path


def data_fixture(
    file_path: str,
    description: str = "",
    loader: Callable[[Path], Any] | None = None,
) -> Callable:
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

    def wrapper(obj: Any) -> Any:
        _fixture_registry[obj.__name__] = {
            "obj": obj,
            "path": Path(file_path),
            "description": description,
            "is_class": isinstance(obj, type),
            "loader": loader,
        }
        logger.debug(f"Registered data fixture: {obj.__name__} -> {file_path}")
        return obj

    return wrapper


def register_loader(extension: str, loader: Callable[[Path], Any]) -> None:
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


def _resolve_data(
    path: Path,
    custom_loader: Callable[[Path], Any] | None,
) -> Any:
    """Load data using custom loader if provided, otherwise the default registry."""
    if custom_loader:
        return custom_loader(path)
    return _load_data(path)


def _build_class_fixture(
    name: str,
    obj: type,
    path: Path,
    description: str,
    custom_loader: Callable[[Path], Any] | None,
) -> Callable:
    """Internal helper to build a class-based pytest fixture."""

    @pytest.fixture(name=name)
    def _class_fixture() -> Any:
        try:
            data = _resolve_data(path, custom_loader)
            return obj(data, description=description)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Fixture '{name}': data file not found at '{path}'. "
                f"Check that fingest_fixture_path is set correctly in pytest.ini."
            ) from None
        except Exception as e:
            logger.error(f"Fixture '{name}' failed (file: {path}): {e}")
            raise

    return _class_fixture


def _build_func_fixture(
    name: str,
    obj: Callable,
    path: Path,
    description: str,
    custom_loader: Callable[[Path], Any] | None,
) -> Callable:
    """Internal helper to build a function-based pytest fixture."""
    sig = inspect.signature(obj)
    params = list(sig.parameters.values())

    # Strip the leading `data` / `self` parameter that fingest injects.
    new_params = params[1:] if params and params[0].name in ("data", "self") else params

    new_sig = sig.replace(parameters=new_params)

    def _wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            data = _resolve_data(path, custom_loader)
            result = obj(data, *args, **kwargs)
            # Attach description to the result when possible.
            if hasattr(result, "_description"):
                result._description = description
            return result
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Fixture '{name}': data file not found at '{path}'. "
                f"Check that fingest_fixture_path is set correctly in pytest.ini."
            ) from None
        except Exception as e:
            logger.error(f"Fixture '{name}' failed (file: {path}): {e}")
            raise

    # Patch the wrapper so pytest sees the correct dependency signature.
    _wrapper.__signature__ = new_sig
    _wrapper.__name__ = obj.__name__
    _wrapper.__doc__ = obj.__doc__
    _wrapper.__module__ = obj.__module__

    return pytest.fixture(name=name)(_wrapper)


def _build_pytest_fixture(
    name: str,
    obj: Any,
    path: Path,
    description: str,
    custom_loader: Callable[[Path], Any] | None = None,
) -> Callable:
    """Build a pytest fixture from a registered data fixture definition."""

    if isinstance(obj, type):
        return _build_class_fixture(name, obj, path, description, custom_loader)

    return _build_func_fixture(name, obj, path, description, custom_loader)


def pytest_sessionstart(session: Any) -> None:
    """Generate real pytest fixtures at test session start."""
    data_root = getattr(session.config, "fingest_fixture_path", "data")

    for name, info in _fixture_registry.items():
        fixture_func = _build_pytest_fixture(
            name=name,
            obj=info["obj"],
            path=Path(data_root) / info["path"],
            description=info["description"],
            custom_loader=info.get("loader"),
        )
        globals()[name] = fixture_func
