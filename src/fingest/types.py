"""Type definitions and base classes for fingest fixtures."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from lxml import etree

# Constants
_NOT_DICT_ERROR = "Data is not a dictionary"


class BaseFixture:
    """Base class for all data fixtures.

    Provides common functionality for accessing and manipulating loaded data.
    """

    def __init__(self, data: Any) -> None:
        """Initialize the fixture with loaded data.

        Args:
            data: The loaded data from the file.
        """
        self._data = data

    @property
    def data(self) -> Any:
        """Get the raw data."""
        return self._data

    def __len__(self) -> int:
        """Return the length of the data if applicable."""
        try:
            return len(self._data)
        except TypeError:
            return 0

    def __bool__(self) -> bool:
        """Return True if data exists and is not empty."""
        if self._data is None:
            return False
        try:
            return len(self._data) > 0
        except TypeError:
            return bool(self._data)

    def __repr__(self) -> str:
        """Return a string representation of the fixture."""
        return f"{self.__class__.__name__}(data={repr(self._data)})"


class JSONFixture(BaseFixture):
    """Fixture for JSON data with dictionary/list-specific methods."""

    def __init__(self, data: Union[Dict, List]) -> None:
        """Initialize with JSON data.

        Args:
            data: Parsed JSON data (dict or list).
        """
        super().__init__(data)

    def keys(self):
        """Get keys if data is a dictionary."""
        if isinstance(self._data, dict):
            return self._data.keys()
        raise TypeError(_NOT_DICT_ERROR)

    def values(self):
        """Get values if data is a dictionary."""
        if isinstance(self._data, dict):
            return self._data.values()
        raise TypeError(_NOT_DICT_ERROR)

    def items(self):
        """Get items if data is a dictionary."""
        if isinstance(self._data, dict):
            return self._data.items()
        raise TypeError(_NOT_DICT_ERROR)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key if data is a dictionary."""
        if isinstance(self._data, dict):
            return self._data.get(key, default)
        raise TypeError(_NOT_DICT_ERROR)

    def length(self) -> int:
        """Get the length of the data."""
        return len(self._data)

    def __getitem__(self, key: Union[str, int]) -> Any:
        """Allow direct indexing of the data."""
        return self._data[key]


class CSVFixture(BaseFixture):
    """Fixture for CSV data with row-specific methods."""

    def __init__(self, data: List[Dict[str, str]]) -> None:
        """Initialize with CSV data.

        Args:
            data: List of dictionaries representing CSV rows.
        """
        super().__init__(data)

    @property
    def rows(self) -> List[Dict[str, str]]:
        """Get all rows."""
        return self._data

    @property
    def columns(self) -> List[str]:
        """Get column names."""
        if self._data:
            return list(self._data[0].keys())
        return []

    def get_column(self, column_name: str) -> List[str]:
        """Get all values from a specific column."""
        return [row.get(column_name, '') for row in self._data]

    def filter_rows(self, **kwargs) -> List[Dict[str, str]]:
        """Filter rows based on column values."""
        filtered = []
        for row in self._data:
            match = True
            for key, value in kwargs.items():
                if row.get(key) != str(value):
                    match = False
                    break
            if match:
                filtered.append(row)
        return filtered

    def __getitem__(self, index: int) -> Dict[str, str]:
        """Get a specific row by index."""
        return self._data[index]


class XMLFixture(BaseFixture):
    """Fixture for XML data with XML-specific methods."""

    def __init__(self, data: etree._ElementTree) -> None:
        """Initialize with XML data.

        Args:
            data: Parsed XML ElementTree.
        """
        super().__init__(data)

    @property
    def root(self) -> etree._Element:
        """Get the root element."""
        return self._data.getroot()

    def find(self, path: str) -> Optional[etree._Element]:
        """Find the first element matching the XPath."""
        return self.root.find(path)

    def findall(self, path: str) -> List[etree._Element]:
        """Find all elements matching the XPath."""
        return self.root.findall(path)

    def xpath(self, path: str) -> List[Any]:
        """Execute an XPath query."""
        return self.root.xpath(path)

    def get_text(self, path: str, default: str = "") -> str:
        """Get text content of the first element matching the XPath."""
        element = self.find(path)
        return element.text if element is not None and element.text else default
