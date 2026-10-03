# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for followed-map bearing stabilization."""

import math

import pytest

from controllers.map_renderer.map_camera_runtime import MapCameraRuntime


def _runtime_for_filter() -> MapCameraRuntime:
    runtime = object.__new__(MapCameraRuntime)
    runtime._filtered_bearing_rad = None
    return runtime


def test_first_bearing_is_applied_immediately() -> None:
    runtime = _runtime_for_filter()

    result = runtime._filter_bearing(math.radians(90.0))

    assert result == pytest.approx(math.radians(90.0))


def test_small_bearing_jitter_is_suppressed() -> None:
    runtime = _runtime_for_filter()
    runtime._filter_bearing(math.radians(90.0))

    assert runtime._filter_bearing(math.radians(92.0)) is None
    assert runtime._filtered_bearing_rad == pytest.approx(math.radians(90.0))


def test_real_turn_is_smoothed() -> None:
    runtime = _runtime_for_filter()
    runtime._filter_bearing(math.radians(90.0))

    result = runtime._filter_bearing(math.radians(130.0))

    assert result == pytest.approx(math.radians(104.0))


def test_bearing_smoothing_uses_short_path_across_north() -> None:
    runtime = _runtime_for_filter()
    runtime._filter_bearing(math.radians(359.0))

    result = runtime._filter_bearing(math.radians(9.0))

    assert result == pytest.approx(math.radians(2.5))


def test_angular_delta_uses_shortest_direction() -> None:
    assert math.degrees(
        MapCameraRuntime._angular_delta(math.radians(359.0), math.radians(1.0))
    ) == pytest.approx(2.0)
    assert math.degrees(
        MapCameraRuntime._angular_delta(math.radians(1.0), math.radians(359.0))
    ) == pytest.approx(-2.0)
