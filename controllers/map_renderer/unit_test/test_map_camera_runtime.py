# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for followed-map bearing stabilization."""

import math
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from controllers.map_renderer.map_camera_runtime import MapCameraRuntime
from controllers.map_renderer.map_request_handler import MapRequestHandler
from ui.navigation import GeoPoint


def test_split_renderer_replay_keeps_the_last_observed_zoom_and_camera():
    runtime = _camera_runtime()
    center = GeoPoint(math.radians(42.51), math.radians(-83.04))
    runtime._handler.observe_camera(center, 17.75, math.radians(25), math.radians(40))
    runtime._renderer_client.reset_mock()
    runtime.request_replay_map_presentation()
    values = runtime._renderer_client.set_camera.call_args.kwargs
    assert values['zoom'] == 17.75
    assert values['latitude'] == pytest.approx(42.51)
    assert values['longitude'] == pytest.approx(-83.04)
    assert runtime._handler.zoom_level == 17.75


def _camera_runtime():
    runtime = _runtime_for_filter()
    runtime._renderer_client = Mock()
    runtime._position_observers = []
    runtime._last_dispatch_error = None
    runtime._current_position = GeoPoint(0.0, 0.0)
    runtime._course_reference = runtime._current_position
    runtime._motion_course_available = False
    runtime._moving = False
    runtime._handler = MapRequestHandler(
        runtime._renderer_client, center=runtime._current_position, bearing_rad=math.pi / 2,
    )
    return runtime


def test_failed_optional_observer_does_not_block_vehicle_or_recenter(caplog):
    runtime = _camera_runtime()
    failed = Mock(side_effect=RuntimeError('optional view unavailable'))
    healthy = Mock()
    runtime._position_observers = [failed, healthy]
    point = _position(math.radians(42.5), math.radians(-83.1))
    runtime._on_position_message(point)
    healthy.assert_called_once()
    runtime._renderer_client.set_position.assert_called_once_with(latitude=42.5, longitude=-83.1)
    runtime._handler.request_recenter()
    camera = runtime._renderer_client.set_camera.call_args.kwargs
    assert camera['latitude'] == pytest.approx(42.5)
    assert camera['longitude'] == pytest.approx(-83.1)
    assert 'Map position dispatch failed' in caplog.text


def test_repeated_dispatch_errors_are_logged_once(caplog):
    runtime = _camera_runtime()
    runtime._on_dispatch_error('openroad.navigation.position', ValueError('position data has missing or unknown fields'))
    runtime._on_dispatch_error('openroad.navigation.position', ValueError('position data has missing or unknown fields'))
    assert caplog.text.count('Map position dispatch failed') == 1


def _motion(speed, course=None, *, cached=False):
    return SimpleNamespace(data=SimpleNamespace(
        ground_speed_m_s=speed, course_rad=course, heading_rad=None, is_cached=cached,
    ))


def _position(latitude, longitude):
    return SimpleNamespace(data=SimpleNamespace(
        latitude_rad=latitude, longitude_rad=longitude, altitude_m=None, fix_mode=3, is_cached=False,
    ))


@pytest.mark.parametrize("speed", [None, 0.0, 0.5, 1.49, float("nan")])
def test_stationary_position_drift_does_not_rotate_camera(speed):
    runtime = _camera_runtime()
    runtime._on_motion_message(_motion(speed, math.pi))
    # Ten metres of GPS drift exceeds the old four-metre course threshold.
    runtime._on_position_message(_position(10 / 6_378_137, 0.0))
    runtime._on_position_message(_position(0.0, -10 / 6_378_137))
    assert runtime._handler.bearing_rad == pytest.approx(math.pi / 2)
    assert runtime._renderer_client.set_position.call_count == 2


def test_cached_motion_does_not_enable_position_heading():
    runtime = _camera_runtime()
    runtime._on_motion_message(_motion(10.0, math.pi, cached=True))
    runtime._on_position_message(_position(10 / 6_378_137, 0.0))
    assert runtime._handler.bearing_rad == pytest.approx(math.pi / 2)


def test_moving_position_fallback_still_tracks_course():
    runtime = _camera_runtime()
    runtime._on_motion_message(_motion(3.0))
    runtime._on_position_message(_position(10 / 6_378_137, 0.0))
    assert runtime._handler.bearing_rad == pytest.approx(0.0)


def test_stopping_holds_last_moving_bearing_despite_drift():
    runtime = _camera_runtime()
    runtime._on_motion_message(_motion(3.0, math.pi))
    bearing = runtime._handler.bearing_rad
    runtime._on_motion_message(_motion(0.0, 0.0))
    runtime._on_position_message(_position(10 / 6_378_137, 0.0))
    assert runtime._handler.bearing_rad == bearing


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


@pytest.mark.parametrize('cached,fix_mode,latitude', [(False,3,.7),(True,3,.7),(False,1,.7),(False,3,None)])
def test_live_position_observer_excludes_cached_or_missing_fixes(cached,fix_mode,latitude):
    runtime = _camera_runtime()
    observer = Mock()
    runtime.observe_position(observer)
    message = _position(latitude,-1.4)
    message.data.is_cached = cached
    message.data.fix_mode = fix_mode
    runtime._on_position_message(message)
    expected = GeoPoint(.7,-1.4) if not cached and fix_mode == 3 and latitude is not None else None
    observer.assert_called_once_with(expected)
