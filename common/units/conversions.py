# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Pure conversion functions for OpenRoadCode's SI-normalized values."""

from __future__ import annotations

import math


def meters_per_second_to_miles_per_hour(value: float | None) -> float | None:
    """Convert meters per second to statute miles per hour."""
    return None if value is None else value * 2.2369362920544


def meters_per_second_to_kilometers_per_hour(value: float | None) -> float | None:
    """Convert meters per second to kilometers per hour."""
    return None if value is None else value * 3.6


def kelvin_to_celsius(value: float | None) -> float | None:
    """Convert absolute temperature in kelvin to degrees Celsius."""
    return None if value is None else value - 273.15


def kelvin_to_fahrenheit(value: float | None) -> float | None:
    """Convert absolute temperature in kelvin to degrees Fahrenheit."""
    celsius = kelvin_to_celsius(value)
    return None if celsius is None else celsius * 9.0 / 5.0 + 32.0


def pascals_to_psi(value: float | None) -> float | None:
    """Convert pascals to pounds per square inch."""
    return None if value is None else value * 0.00014503773773020923


def pascals_to_kilopascals(value: float | None) -> float | None:
    """Convert pascals to kilopascals."""
    return None if value is None else value * 0.001


def meters_to_feet(value: float | None) -> float | None:
    """Convert meters to international feet."""
    return None if value is None else value * 3.280839895013123


def radians_to_degrees(value: float | None) -> float | None:
    """Convert radians to degrees."""
    return None if value is None else math.degrees(value)


def radians_per_second_to_rpm(value: float | None) -> float | None:
    """Convert angular velocity in radians per second to revolutions per minute."""
    return None if value is None else value * 60.0 / (2.0 * math.pi)


def kilograms_per_second_to_grams_per_second(value: float | None) -> float | None:
    """Convert kilograms per second to grams per second."""
    return None if value is None else value * 1000.0
