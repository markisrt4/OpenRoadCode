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


def test_renderer_restart_replays_true_vehicle_position():
    from unittest.mock import Mock
    from ui.navigation import GeoPoint

    runtime = object.__new__(MapCameraRuntime)
    runtime._renderer_client = Mock()
    runtime._current_position = GeoPoint(math.radians(42.8), math.radians(-83.0))
    runtime.refresh_renderer_position()
    runtime._renderer_client.set_position.assert_called_once_with(latitude=42.8, longitude=-83.0)


def test_renderer_restart_does_not_invent_missing_vehicle_position():
    from unittest.mock import Mock

    runtime = object.__new__(MapCameraRuntime)
    runtime._renderer_client = Mock()
    runtime._current_position = None
    runtime.refresh_renderer_position()
    runtime._renderer_client.set_position.assert_not_called()
