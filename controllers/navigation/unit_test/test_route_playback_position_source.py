# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Verify playback arbitration and stale callback rejection without a receiver."""

from unittest.mock import Mock
import threading

import pytest

from controllers.navigation.navigation_state import PositionState
from controllers.navigation.route_playback_position_source import RoutePlaybackPositionSource
from controllers.navigation.simulated_position_source import SimulatedPositionSource
from controllers.route_planning.route_planning_types import GeoPoint, RouteResult


def _route():
    return RouteResult(1.0, 120.0, (GeoPoint(42.0, -83.0), GeoPoint(42.0, -82.99)), ())


def _sources():
    live, simulator = Mock(), Mock(spec=SimulatedPositionSource)
    source = RoutePlaybackPositionSource(live, simulator)
    received = []
    source.start(received.append)
    return source, live, simulator, received


def test_playback_keeps_receiver_running_and_resumes_only_fresh_live_reports():
    source, live, simulator, received = _sources()
    live_report = live.start.call_args.args[0]
    real = PositionState(source="android")
    simulated = PositionState(source="route-simulation")
    live_report(real)
    source.follow_route(_route(), time_scale=30.0)
    playback_report = simulator.start.call_args.args[0]
    simulator.follow_route.assert_called_once_with(_route(), time_scale=30.0)
    live.stop.assert_not_called()
    live_report(real)
    playback_report(simulated)
    assert received == [real, simulated]

    source.stop_route()
    playback_report(simulated)
    assert received == [real, simulated]
    live_report(real)
    assert received == [real, simulated, real]
    source.stop()
    live.stop.assert_called_once()


def test_replacement_playback_and_restart_reject_old_callbacks():
    source, live, simulator, received = _sources()
    old_live = live.start.call_args.args[0]
    source.follow_route(_route())
    old_playback = simulator.start.call_args.args[0]
    source.follow_route(_route())
    current_playback = simulator.start.call_args.args[0]
    old_playback(PositionState())
    assert received == []
    current_playback(PositionState(source="route-simulation"))
    assert len(received) == 1
    source.stop()
    current_playback(PositionState())
    old_live(PositionState())
    source.start(received.append)
    old_live(PositionState())
    old_playback(PositionState())
    current_playback(PositionState())
    assert len(received) == 1
    live.start.call_args.args[0](PositionState(source="android"))
    assert received[-1].source == "android"
    source.stop()


@pytest.mark.parametrize("failure", ["route", "start"])
def test_failed_playback_restores_live_delivery(failure):
    source, live, simulator, received = _sources()
    method = simulator.follow_route if failure == "route" else simulator.start
    method.side_effect = ValueError("invalid playback")
    with pytest.raises(ValueError, match="invalid playback"):
        source.follow_route(_route())
    live.start.call_args.args[0](PositionState(source="android"))
    assert received[-1].source == "android"
    source.stop()


def test_playback_requires_started_source_and_failed_live_start_can_be_retried():
    live = Mock()
    source = RoutePlaybackPositionSource(live, Mock(spec=SimulatedPositionSource))
    with pytest.raises(RuntimeError, match="not running"):
        source.follow_route(_route())
    live.start.side_effect = RuntimeError("receiver unavailable")
    with pytest.raises(RuntimeError, match="receiver unavailable"):
        source.start(Mock())
    stale = live.start.call_args.args[0]
    live.start.side_effect = None
    received = []
    source.start(received.append)
    stale(PositionState())
    assert received == []
    source.stop()


@pytest.mark.parametrize("scale", [0.0, -1.0, float("nan"), float("inf")])
def test_route_simulator_rejects_invalid_time_scales(scale):
    simulator = SimulatedPositionSource()
    with pytest.raises(ValueError, match="greater than zero"):
        simulator.follow_route(_route(), time_scale=scale)


def test_real_playback_thread_delivers_route_positions_and_stops_cleanly():
    live = Mock()
    simulator = SimulatedPositionSource(update_rate_hz=50.0)
    source = RoutePlaybackPositionSource(live, simulator)
    arrived = threading.Event()
    received = []

    def receive(state):
        received.append(state)
        if state.source == "route-simulation" and state.speed_mps == 0.0:
            arrived.set()

    source.start(receive)
    source.start(receive)
    live.start.assert_called_once()
    try:
        source.follow_route(_route(), time_scale=1200.0)
        assert arrived.wait(timeout=2.0)
        source.stop_route()
        count = len(received)
        assert received[-1].longitude_deg == pytest.approx(-82.99)
        assert all(state.source == "route-simulation" for state in received)
        live.start.call_args.args[0](PositionState(source="android"))
        assert len(received) == count + 1
        assert received[-1].source == "android"
        assert simulator._thread is None
    finally:
        source.stop()
