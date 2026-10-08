# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable unit conversions for SI-normalized OpenRoadCode data."""

from common.units.conversions import (
    celsius_to_kelvin,
    hectopascals_to_pascals,
    kilometers_per_hour_to_meters_per_second,
    millimeters_to_meters,
    percent_to_ratio,
    kelvin_to_celsius,
    kelvin_to_fahrenheit,
    kilograms_per_second_to_grams_per_second,
    meters_per_second_squared_to_feet_per_second_squared,
    meters_per_second_to_kilometers_per_hour,
    meters_per_second_to_miles_per_hour,
    meters_to_feet,
    pascals_to_kilopascals,
    pascals_to_psi,
    radians_per_second_to_degrees_per_second,
    radians_per_second_to_rpm,
    radians_to_degrees,
)
from common.units.unit_system import UnitSystem

__all__ = [
    "celsius_to_kelvin",
    "hectopascals_to_pascals",
    "kilometers_per_hour_to_meters_per_second",
    "millimeters_to_meters",
    "percent_to_ratio",
    "UnitSystem",
    "kelvin_to_celsius",
    "kelvin_to_fahrenheit",
    "kilograms_per_second_to_grams_per_second",
    "meters_per_second_squared_to_feet_per_second_squared",
    "meters_per_second_to_kilometers_per_hour",
    "meters_per_second_to_miles_per_hour",
    "meters_to_feet",
    "pascals_to_kilopascals",
    "pascals_to_psi",
    "radians_per_second_to_degrees_per_second",
    "radians_per_second_to_rpm",
    "radians_to_degrees",
]
