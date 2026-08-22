# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for reusable SI presentation-unit conversions."""

import math

import pytest

from common.units import (
    kelvin_to_celsius,
    kelvin_to_fahrenheit,
    kilograms_per_second_to_grams_per_second,
    meters_per_second_to_kilometers_per_hour,
    meters_per_second_to_miles_per_hour,
    meters_to_feet,
    pascals_to_kilopascals,
    pascals_to_psi,
    radians_per_second_to_rpm,
    radians_to_degrees,
)


@pytest.mark.parametrize(
    ("converter", "value", "expected"),
    [
        (meters_per_second_to_miles_per_hour, 1.0, 2.2369362920544),
        (meters_per_second_to_kilometers_per_hour, 10.0, 36.0),
        (kelvin_to_celsius, 273.15, 0.0),
        (kelvin_to_fahrenheit, 273.15, 32.0),
        (pascals_to_psi, 6894.757293168, 1.0),
        (pascals_to_kilopascals, 101325.0, 101.325),
        (meters_to_feet, 1.0, 3.280839895013123),
        (radians_to_degrees, math.pi, 180.0),
        (radians_per_second_to_rpm, 2.0 * math.pi, 60.0),
        (kilograms_per_second_to_grams_per_second, 0.0125, 12.5),
    ],
)
def test_conversion_reference_values(converter, value, expected):
    assert converter(value) == pytest.approx(expected)


@pytest.mark.parametrize(
    "converter",
    [
        meters_per_second_to_miles_per_hour,
        meters_per_second_to_kilometers_per_hour,
        kelvin_to_celsius,
        kelvin_to_fahrenheit,
        pascals_to_psi,
        pascals_to_kilopascals,
        meters_to_feet,
        radians_to_degrees,
        radians_per_second_to_rpm,
        kilograms_per_second_to_grams_per_second,
    ],
)
def test_optional_values_preserve_none(converter):
    assert converter(None) is None


def test_zero_values_remain_zero_where_physically_applicable():
    assert meters_per_second_to_miles_per_hour(0.0) == 0.0
    assert meters_per_second_to_kilometers_per_hour(0.0) == 0.0
    assert pascals_to_psi(0.0) == 0.0
    assert pascals_to_kilopascals(0.0) == 0.0
    assert meters_to_feet(0.0) == 0.0
    assert radians_to_degrees(0.0) == 0.0
    assert radians_per_second_to_rpm(0.0) == 0.0
    assert kilograms_per_second_to_grams_per_second(0.0) == 0.0
