"""Type definitions and base classes for fingest fixtures."""

from collections.abc import Callable, Iterator
from typing import Any

from lxml import etree

# Constants
_NOT_DICT_ERROR = "Data is not a dictionary"
_REPR_MAX_LEN = 80


class BaseFixture:
    """Base class for all data fixtures.

    Provides common functionality for accessing and manipulating loaded data.
    Supports iteration, containment checks, and equality comparison.
    """

    def __init__(self, data: Any, *, description: str = "") -> None:
        """Initialize the fixture with loaded data.

        Args:
            data: The loaded data from the file.
            description: Optional human-readable description for debugging.
        """
        self._data = data
        self._description = description

    @property
    def data(self) -> Any:
        """Get the raw data."""
        return self._data

    @property
    def description(self) -> str:
        """Get the fixture description."""
        return self._description

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

    def __iter__(self) -> Iterator:
        """Iterate over the underlying data."""
        return iter(self._data)

    def __contains__(self, item: Any) -> bool:
        """Check if an item is in the underlying data."""
        return item in self._data

    def __eq__(self, other: object) -> bool:
        """Compare fixtures by data and description."""
        if not isinstance(other, BaseFixture):
            return NotImplemented
        return self._data == other._data and self._description == other._description

    def _truncated_data_repr(self) -> str:
        """Return a truncated repr of the data for human-friendly output."""
        raw = repr(self._data)
        if len(raw) > _REPR_MAX_LEN:
            return raw[: _REPR_MAX_LEN - 3] + "..."
        return raw

    def __repr__(self) -> str:
        """Return a string representation of the fixture."""
        if self._description:
            return f"{self.__class__.__name__}({self._description!r})"
        return f"{self.__class__.__name__}(data={self._truncated_data_repr()})"

    def __str__(self) -> str:
        """Return a detailed string representation."""
        if self._description:
            return (
                f"{self.__class__.__name__}("
                f"data={self._truncated_data_repr()}, "
                f"description={self._description!r})"
            )
        return repr(self)


class JSONFixture(BaseFixture):
    """Fixture for JSON data with dictionary/list-specific methods."""

    def __init__(self, data: dict | list, **kwargs: Any) -> None:
        """Initialize with JSON data.

        Args:
            data: Parsed JSON data (dict or list).
            **kwargs: Passed to BaseFixture (e.g. description).
        """
        super().__init__(data, **kwargs)

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

    def __getitem__(self, key: str | int) -> Any:
        """Allow direct indexing of the data."""
        return self._data[key]

    def __iter__(self) -> Iterator:
        """Iterate over keys (dict) or items (list)."""
        return iter(self._data)

    def __contains__(self, item: Any) -> bool:
        """Check containment — keys for dicts, items for lists."""
        return item in self._data


class CSVFixture(BaseFixture):
    """Fixture for CSV data with row-specific methods."""

    def __init__(self, data: list[dict[str, str]], **kwargs: Any) -> None:
        """Initialize with CSV data.

        Args:
            data: List of dictionaries representing CSV rows.
            **kwargs: Passed to BaseFixture (e.g. description).
        """
        super().__init__(data, **kwargs)

    @property
    def rows(self) -> list[dict[str, str]]:
        """Get all rows."""
        return self._data

    @property
    def row_count(self) -> int:
        """Get the number of rows."""
        return len(self._data)

    @property
    def columns(self) -> list[str]:
        """Get column names."""
        if self._data:
            return list(self._data[0].keys())
        return []

    def get_column(self, column_name: str) -> list[str]:
        """Get all values from a specific column."""
        return [row.get(column_name, "") for row in self._data]

    def filter_rows(
        self, **kwargs: str | Callable[[str], bool]
    ) -> list[dict[str, str]]:
        """Filter rows based on column values or predicates.

        Each keyword argument can be either a literal string value for exact
        matching, or a callable that receives the column value and returns a
        bool.

        Examples:
            fixture.filter_rows(city="NYC")
            fixture.filter_rows(price=lambda p: float(p) > 100)
        """
        filtered = []
        for row in self._data:
            match = True
            for key, value in kwargs.items():
                cell = row.get(key)
                if callable(value):
                    if not value(cell):
                        match = False
                        break
                else:
                    if cell != str(value):
                        match = False
                        break
            if match:
                filtered.append(row)
        return filtered

    def __getitem__(self, index: int) -> dict[str, str]:
        """Get a specific row by index."""
        return self._data[index]

    def __iter__(self) -> Iterator[dict[str, str]]:
        """Iterate over rows."""
        return iter(self._data)

    def __contains__(self, item: Any) -> bool:
        """Check if a row dict is in the data."""
        return item in self._data


class XMLFixture(BaseFixture):
    """Fixture for XML data with XML-specific methods."""

    def __init__(self, data: etree._ElementTree, **kwargs: Any) -> None:
        """Initialize with XML data.

        Args:
            data: Parsed XML ElementTree.
            **kwargs: Passed to BaseFixture (e.g. description).
        """
        super().__init__(data, **kwargs)

    @property
    def root(self) -> etree._Element:
        """Get the root element."""
        return self._data.getroot()

    @property
    def tag(self) -> str:
        """Get the root element's tag name."""
        return self.root.tag

    def find(self, path: str) -> etree._Element | None:
        """Find the first element matching the XPath."""
        return self.root.find(path)

    def findall(self, path: str) -> list[etree._Element]:
        """Find all elements matching the XPath."""
        return self.root.findall(path)

    def xpath(self, path: str) -> list[Any]:
        """Execute an XPath query."""
        return self.root.xpath(path)

    def get_text(self, path: str, default: str = "") -> str:
        """Get text content of the first element matching the XPath."""
        element = self.find(path)
        return element.text if element is not None and element.text else default

    def to_dict(self) -> dict[str, Any]:
        """Recursively convert the XML tree to a plain dictionary.

        Attributes are stored under an ``"@attr"`` key; text content under
        ``"#text"``.  Repeated child tags become lists automatically.
        """

        def _element_to_dict(el: etree._Element) -> dict[str, Any]:
            result: dict[str, Any] = {}

            # Attributes
            for attr_name, attr_val in el.attrib.items():
                result[f"@{attr_name}"] = attr_val

            # Children
            for child in el:
                child_dict = _element_to_dict(child)
                if child.tag in result:
                    existing = result[child.tag]
                    if not isinstance(existing, list):
                        result[child.tag] = [existing]
                    result[child.tag].append(child_dict)
                else:
                    result[child.tag] = child_dict

            # Text
            text = (el.text or "").strip()
            if text:
                if result:
                    result["#text"] = text
                else:
                    return text  # type: ignore[return-value]

            return result

        return {self.root.tag: _element_to_dict(self.root)}
