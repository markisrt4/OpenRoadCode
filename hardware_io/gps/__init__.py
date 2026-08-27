# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""GPS hardware contracts and optional gpsd-backed implementation."""

from importlib import import_module
from typing import Any

__all__ = [
    "GpsData",
    "GpsReader",
]


def __getattr__(name: str) -> Any:
    """Load the gpsd-backed implementation only when explicitly requested."""
    if name not in {"GpsData", "GpsReader"}:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module("hardware_io.gps.gps_reader")
    value = getattr(module, name)
    globals()[name] = value
    return value
