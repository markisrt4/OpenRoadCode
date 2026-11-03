# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from datetime import timezone
from types import SimpleNamespace
from unittest.mock import Mock

from controllers.navigation.android_position_source import AndroidPositionSource
from controllers.navigation.navigation_controller import NavigationController
from controllers.navigation.navigation_state import PositionState
from controllers.navigation.simulated_navigation_sensor import SimulatedNavigationSensor
from messaging.contracts.navigation.position_state_codec import encode_position_state


def test_explicit_host_fix_has_bounded_precedence_and_simulation_can_suspend_it():
    now = [100]
    controller = NavigationController(SimulatedNavigationSensor('stationary'), monotonic_clock=lambda: now[0])
    controller.start()
    try:
        primary = PositionState(latitude_deg=42, longitude_deg=-83, fix_mode=3, source='android-gps')
        host = PositionState(latitude_deg=43, longitude_deg=-84, fix_mode=2, source='browser')
        controller.update_position_state(primary)
        controller.update_host_position_state(host)
        controller.update_position_state(primary)
        assert controller.read_state().position == host
        controller.set_host_location_suspended(True)
        assert controller.read_state().position == primary
        controller.set_host_location_suspended(False)
        assert controller.read_state().position == host
        now[0] = 111
        assert controller.read_state().position == primary
    finally:
        controller.stop()


def test_position_default_timestamp_is_unambiguous_utc():
    import time
    state = PositionState()
    assert state.received_at.tzinfo == timezone.utc
    assert abs(encode_position_state(state)['timestamp']['seconds'] - time.time()) < 2


def test_android_source_preserves_sample_time_instead_of_retimestamping_old_fix():
    client = Mock()
    client.read_location.return_value = SimpleNamespace(timestamp_ms=1793660782000,
        latitude_deg=42, longitude_deg=-83, altitude_m=None, speed_mps=None,
        bearing_deg=None, horizontal_accuracy_m=20, provider='gps')
    source = AndroidPositionSource(client)
    positions = []

    def capture(state):
        positions.append(state)
        source._stop_event.set()

    source._run(capture)
    assert encode_position_state(positions[0])['timestamp']['seconds'] == 1793660782
    assert positions[0].received_at.tzinfo == timezone.utc
