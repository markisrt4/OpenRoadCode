# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for followed-map bearing stabilization."""

import math
import time
from itertools import count
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from controllers.map_renderer.map_camera_runtime import MapCameraRuntime
from controllers.map_renderer.map_request_handler import MapRequestHandler
from ui.navigation import GeoPoint


def _camera_runtime():
    runtime = _runtime_for_filter()
    runtime._renderer_client = Mock()
    runtime._current_position = GeoPoint(0.0, 0.0)
    runtime._course_reference = runtime._current_position
    runtime._motion_course_available = False
    runtime._moving = False
    runtime._closed = False
    runtime._marker_heading_rad = None
    runtime._motion_course_rad = None
    runtime._motion_speed_m_s = None
    runtime._motion_received_at = 0.0
    runtime._position_timestamp = None
    runtime._motion_timestamp = None
    runtime._handler = MapRequestHandler(
        runtime._renderer_client, center=runtime._current_position, bearing_rad=math.pi / 2,
    )
    return runtime


_motion_seconds = count(1)


def _motion(speed, course=None, *, cached=False, seconds=None):
    return SimpleNamespace(timestamp=SimpleNamespace(
        seconds=next(_motion_seconds) if seconds is None else seconds, nanoseconds=0,
    ), data=SimpleNamespace(
        ground_speed_m_s=speed, course_rad=course, heading_rad=None, is_cached=cached,
    ))


_position_seconds = count(1)


def _position(latitude, longitude, *, seconds=None, cached=False):
    return SimpleNamespace(timestamp=SimpleNamespace(
        seconds=next(_position_seconds) if seconds is None else seconds, nanoseconds=0,
    ), data=SimpleNamespace(
        latitude_rad=latitude, longitude_rad=longitude, altitude_m=None, is_cached=cached,
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
    runtime._marker_heading_rad = None
    runtime.refresh_renderer_position()
    runtime._renderer_client.set_position.assert_called_once_with(latitude=42.8, longitude=-83.0)


def test_renderer_restart_does_not_invent_missing_vehicle_position():
    from unittest.mock import Mock

    runtime = object.__new__(MapCameraRuntime)
    runtime._renderer_client = Mock()
    runtime._current_position = None
    runtime.refresh_renderer_position()
    runtime._renderer_client.set_position.assert_not_called()


def test_live_fix_requests_smoothing_with_course_and_speed():
    runtime = _camera_runtime()
    runtime._on_motion_message(_motion(12.0, math.pi / 2))
    runtime._on_position_message(_position(0.0, 0.0))
    marker = runtime._renderer_client.set_position.call_args.kwargs
    assert marker["smooth"] is True
    assert marker["heading_deg"] == pytest.approx(90)
    assert marker["course_deg"] == pytest.approx(90)
    assert marker["speed_m_s"] == 12
    assert runtime._renderer_client.set_camera.call_args.kwargs["follow_position"] is True


def test_relative_imu_heading_is_not_used_as_map_direction():
    runtime = _camera_runtime()
    motion = _motion(12.0)
    motion.data.heading_rad = math.pi
    runtime._on_motion_message(motion)
    runtime._on_position_message(_position(0.0, 0.0))
    assert runtime._renderer_client.set_position.call_args.kwargs["heading_deg"] is None


def test_cached_position_is_not_predicted():
    runtime = _camera_runtime()
    runtime._on_position_message(_position(0.0, 0.0, cached=True))
    assert runtime._renderer_client.set_position.call_args.kwargs["smooth"] is False


def test_old_motion_is_not_reused_for_prediction():
    runtime = _camera_runtime()
    runtime._on_motion_message(_motion(12.0, math.pi / 2))
    runtime._motion_received_at = time.monotonic() - 2.0
    runtime._on_position_message(_position(0.0, 0.0))
    marker = runtime._renderer_client.set_position.call_args.kwargs
    assert marker["speed_m_s"] is None
    assert marker["course_deg"] is None
    assert marker["heading_deg"] == pytest.approx(90)


def test_duplicate_and_out_of_order_fixes_do_not_restart_prediction():
    runtime = _camera_runtime()
    runtime._on_position_message(_position(0.0, 0.0, seconds=10))
    runtime._on_position_message(_position(0.1, 0.1, seconds=10))
    runtime._on_position_message(_position(0.1, 0.1, seconds=9))
    assert runtime._renderer_client.set_position.call_count == 1
    assert runtime.current_position == GeoPoint(0.0, 0.0)


def test_out_of_order_motion_does_not_reverse_marker_direction():
    runtime = _camera_runtime()
    runtime._on_motion_message(_motion(12.0, math.pi / 2, seconds=10))
    runtime._on_motion_message(_motion(12.0, math.pi, seconds=9))
    runtime._on_position_message(_position(0.0, 0.0))
    assert runtime._renderer_client.set_position.call_args.kwargs["heading_deg"] == 90


def test_manual_camera_does_not_prevent_vehicle_motion():
    runtime = _camera_runtime()
    runtime._handler.request_follow(False)
    runtime._renderer_client.reset_mock()
    runtime._on_position_message(_position(0.0, 0.0))
    runtime._renderer_client.set_position.assert_called_once()
    runtime._renderer_client.set_camera.assert_not_called()


def test_callbacks_after_close_do_not_send_commands():
    runtime = _camera_runtime()
    runtime._closed = True
    runtime._on_motion_message(_motion(12.0, math.pi / 2))
    runtime._on_position_message(_position(0.0, 0.0))
    assert runtime._renderer_client.mock_calls == []
