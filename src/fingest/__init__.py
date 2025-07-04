"""Fingest - Pytest plugin for data-driven fixtures.

This plugin allows you to easily define data-driven fixtures based on external files.
It supports JSON, CSV, and XML data sources, and can automatically instantiate
Python classes or functions using this data.
"""

from .plugin import data_fixture, register_loader
from .types import BaseFixture, JSONFixture, CSVFixture, XMLFixture

__version__ = "0.1.0"
__author__ = "Tim Fiedler"
__email__ = "tim@0x68.de"

__all__ = [
    "data_fixture",
    "register_loader",
    "BaseFixture",
    "JSONFixture",
    "CSVFixture",
    "XMLFixture"
]