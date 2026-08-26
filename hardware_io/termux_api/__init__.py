# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Low-level access to Android hardware exposed through Termux:API."""

from hardware_io.termux_api.termux_location import TermuxLocationClient, TermuxLocationData
from hardware_io.termux_api.termux_sensor import TermuxSensorClient

__all__ = [
    "TermuxLocationClient",
    "TermuxLocationData",
    "TermuxSensorClient",
]
