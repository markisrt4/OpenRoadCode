# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""GPS hardware contracts and optional gpsd-backed implementation."""

from importlib import import_module
from typing import Any

from hardware_io.gps.gps_types import GpsCallback, GpsData

__all__ = [
    "GpsCallback",
    "GpsData",
    "GpsReader",
]


def __getattr__(name: str) -> Any:
    """Load the gpsd-backed reader only when explicitly requested."""
    if name != "GpsReader":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module("hardware_io.gps.gps_reader")
    value = module.GpsReader
    globals()[name] = value
    return value
