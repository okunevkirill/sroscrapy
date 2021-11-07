# Author: ok_kir <clicktmin@gmail.com>
"""
Site scan package for obtaining information on checks in self-regulatory organizations
"""

import sys

from .exceptions import *

__version__ = "0.00.10"
__all__ = [
    "SroScraperError",
    "FileDataError",
    "URLError",
    "kernel",
    "naufor"
]

if sys.version_info.major < 3 or sys.version_info.minor < 7:
    raise ImportError("This package is for Python >= 3.7")
