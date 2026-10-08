# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Automotive logging contracts without hardware or a running broker."""

from datetime import datetime, timedelta
import json
import logging
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from common.logging.structured import JsonFormatter, current_operation, operation, validate_event
from controllers.automotive import AutomotiveTelemetryProfile
from controllers.automotive.navigation_motion_vehicle_state_source import (
    NavigationMotionVehicleStateSource,
)
from controllers.automotive.obd2.elm327_obd_adapter import Elm327ObdAdapter
from controllers.automotive.obd2.obd2_manager import Obd2Manager
from controllers.automotive.trip_tracker import TripTracker
from controllers.automotive.vehicle_state import VehicleState
from controllers.navigation.navigation_state import GroundMotionState, PositionState
from hardware_io.automotive.elm327 import Elm327ConnectionError, Elm327Response
from messaging.contracts.automotive.telemetry_profile_request import (
    AutomotiveTelemetryProfileRequest,
)
from protocols.obd2 import Obd2ConnectionError, Obd2ProtocolError, Obd2Request
from protocols.obd2.simulated_obd2_adapter import SimulatedObd2Adapter
from services.automotive.automotive_runtime import AutomotiveRuntime
from services.automotive.automotive_telemetry_profile_runtime import (
    AutomotiveTelemetryProfileRuntime,
)


def events(caplog):
    result = [
        json.loads(JsonFormatter().format(record))
        for record in caplog.records
        if record.name.startswith("automotive.")
    ]
    for item in result:
        validate_event(item)
    return result


def runtime(source, publisher=None):
    result = AutomotiveRuntime(source, publisher or Mock())
    result._stop_event = Mock()
    return result


def test_reconnect_logs_transitions_once_and_preserves_publication(caplog):
    caplog.set_level(logging.INFO)
    source, publisher = Mock(), Mock()
    source.connect.side_effect = [
        Obd2ConnectionError("private endpoint"),
        Obd2ConnectionError("private endpoint"),
        None,
        None,
    ]
    source.read_state.side_effect = [
        Obd2ConnectionError("private ECU data"),
        VehicleState(timestamp=datetime.now()),
    ]
    service = runtime(source, publisher)
    service._stop_event.is_set.side_effect = [False, False, False, False, True]
    service.run()
    service.close()
    emitted = events(caplog)
    names = [item["event"] for item in emitted]
    assert names.count("source.unavailable") == 1
    assert names.count("source.lost") == 1
    assert names.count("service.stopped") == 1
    connections = [item for item in emitted if item["event"] == "source.connected"]
    assert [item["recovered"] for item in connections] == [True, True]
    assert all(item["operation_id"] for item in connections)
    assert source.disconnect.call_count == 2
    publisher.publish.assert_called_once()
    assert "private" not in json.dumps(emitted)
    assert current_operation() is None


def test_successful_polling_is_quiet_at_info(caplog):
    caplog.set_level(logging.INFO)
    source = Mock()
    source.read_state.return_value = VehicleState(timestamp=datetime.now(), vehicle_speed_m_s=23.45)
    service = runtime(source)
    service._stop_event.is_set.side_effect = [False, False, False, True]
    service.run()
    assert [item["event"] for item in events(caplog)] == [
        "service.started",
        "source.connected",
        "service.stopped",
    ]


@pytest.mark.parametrize("failure_stage", ["read", "publish"])
def test_fatal_failure_is_logged_and_cleanup_runs(caplog, failure_stage):
    caplog.set_level(logging.DEBUG)
    source, publisher = Mock(), Mock()
    source.read_state.return_value = VehicleState(timestamp=datetime.now())
    if failure_stage == "read":
        source.read_state.side_effect = RuntimeError("VIN=private")
    else:
        publisher.publish.side_effect = RuntimeError("VIN=private")
    service = runtime(source, publisher)
    service._stop_event.is_set.return_value = False
    with pytest.raises(RuntimeError):
        service.run()
    emitted = events(caplog)
    failure = next(item for item in emitted if item["event"] == "service.failed")
    assert failure["level"] == "ERROR" and failure["exception_type"] == "RuntimeError"
    assert "state.published" not in [item["event"] for item in emitted]
    assert "private" not in json.dumps(emitted)
    source.disconnect.assert_called_once()


def test_obd_connect_discovery_and_adapter_share_operation(caplog):
    caplog.set_level(logging.DEBUG)
    device = Mock(is_connected=False)
    device.send_command.return_value = Elm327Response(
        command="0100", raw="private raw ECU", lines=("7E806410000180000",)
    )
    manager = Obd2Manager(Elm327ObdAdapter(device))
    service = runtime(manager)
    with operation("connect-test"):
        assert service._try_connect()
    emitted = events(caplog)
    assert {item["event"] for item in emitted} >= {
        "adapter.connected",
        "request.completed",
        "pids.discovered",
        "source.connected",
    }
    assert all(item["operation_id"] == "connect-test" for item in emitted)
    discovery = next(item for item in emitted if item["event"] == "pids.discovered")
    assert discovery["supported_pid_count"] == 2
    assert manager.supported_pids == frozenset({12, 13})
    assert "private" not in json.dumps(emitted)


@pytest.mark.parametrize("response", ["NO DATA", "private malformed ECU frame"])
def test_request_metadata_excludes_raw_response_and_uses_obd_pid(caplog, response):
    caplog.set_level(logging.DEBUG)
    device = Mock(is_connected=True)
    device.send_command.return_value = Elm327Response(
        command="010C", raw=response, lines=(response,)
    )
    adapter = Elm327ObdAdapter(device)
    if response == "NO DATA":
        assert adapter.request(Obd2Request(mode=1, pid=12)) == ()
    else:
        with pytest.raises(Obd2ProtocolError):
            adapter.request(Obd2Request(mode=1, pid=12))
    emitted = events(caplog)
    assert len(emitted) == 1
    assert emitted[0]["obd_pid"] == 12 and emitted[0]["mode"] == 1
    import os

    assert emitted[0]["pid"] == os.getpid()  # OBD PID cannot replace the schema process PID.
    assert emitted[0]["level"] == "DEBUG"
    assert response not in json.dumps(emitted)


def test_connect_failure_does_not_log_success_or_error_text(caplog):
    caplog.set_level(logging.DEBUG)
    device = Mock(is_connected=False)
    device.connect.side_effect = Elm327ConnectionError("secret Bluetooth address")
    with pytest.raises(Obd2ConnectionError):
        Elm327ObdAdapter(device).connect()
    emitted = events(caplog)
    assert [item["event"] for item in emitted] == ["adapter.connect_failed"]
    assert emitted[0]["operation_id"]
    assert "secret" not in json.dumps(emitted)


def test_discovery_failure_keeps_fallback_behavior(caplog):
    caplog.set_level(logging.INFO)
    adapter = Mock()
    adapter.request.side_effect = Obd2ConnectionError("private payload")
    manager = Obd2Manager(adapter)
    manager.connect()
    assert manager.supported_pids is None
    emitted = events(caplog)
    assert emitted[0]["event"] == "pids.discovery_failed"
    assert emitted[0]["level"] == "WARNING"
    assert emitted[1]["discovery_available"] is False
    assert "private" not in json.dumps(emitted)


def test_profile_change_correlates_and_repeated_requests_are_quiet(caplog):
    caplog.set_level(logging.INFO)
    manager = Obd2Manager(SimulatedObd2Adapter())
    profile_runtime = AutomotiveTelemetryProfileRuntime(Mock(), manager)
    request = AutomotiveTelemetryProfileRequest(AutomotiveTelemetryProfile.ECU, "private client")
    profile_runtime._handle_request(request)
    profile_runtime._handle_request(request)
    emitted = events(caplog)
    assert len(emitted) == 1 and emitted[0]["event"] == "polling.profile_changed"
    assert emitted[0]["operation_id"] and emitted[0]["profile"] == "ecu"
    assert "private" not in json.dumps(emitted)
    assert current_operation() is None


def test_profile_failure_has_no_applied_event(caplog):
    caplog.set_level(logging.DEBUG)
    source = Mock()
    source.set_telemetry_profile.side_effect = RuntimeError("private detail")
    profile_runtime = AutomotiveTelemetryProfileRuntime(Mock(), source)
    with pytest.raises(RuntimeError):
        profile_runtime._handle_request(
            AutomotiveTelemetryProfileRequest(AutomotiveTelemetryProfile.ECU, "private source")
        )
    emitted = events(caplog)
    assert [item["event"] for item in emitted] == ["profile.failed"]
    assert emitted[0]["operation_id"] and emitted[0]["level"] == "ERROR"
    assert "private" not in json.dumps(emitted)


def test_trip_lifecycle_keeps_id_and_excludes_driving_data(caplog):
    caplog.set_level(logging.INFO)
    trip = TripTracker(pause_after_s=1)
    start = datetime.now()
    trip.observe_position_state(
        PositionState(latitude_deg=42.123, longitude_deg=-83.456, fix_mode=3)
    )
    for seconds, speed in [(0, 12.34), (1, 12.34), (2, 0), (4, 0), (5, 12.34)]:
        trip.observe_ground_motion_state(
            GroundMotionState(received_at=start + timedelta(seconds=seconds), speed_mps=speed)
        )
    trip.finish()
    trip.finish()
    trip.reset()
    trip.reset()
    emitted = events(caplog)
    assert [item["event"] for item in emitted] == [
        "trip.started",
        "trip.status_changed",
        "trip.status_changed",
        "trip.completed",
        "trip.reset",
    ]
    assert len({item["operation_id"] for item in emitted}) == 1
    assert all(word not in json.dumps(emitted) for word in ["42.123", "-83.456", "12.34"])
    assert not any(
        key in item for item in emitted for key in ["speed", "distance_m", "fuel_used_m3"]
    )
    trip.observe_ground_motion_state(GroundMotionState(speed_mps=1))
    assert events(caplog)[-1]["operation_id"] != emitted[0]["operation_id"]


def test_motion_logs_availability_transitions_without_speed(caplog):
    caplog.set_level(logging.INFO)
    source = NavigationMotionVehicleStateSource(Mock())
    for speed in [None, 12.34, 23.45, None, None, 12.34]:
        source._on_motion_state(
            SimpleNamespace(
                timestamp=SimpleNamespace(seconds=1780000000, nanoseconds=0),
                data=SimpleNamespace(ground_speed_m_s=speed),
            )
        )
    emitted = events(caplog)
    assert [item["available"] for item in emitted] == [True, False, True]
    assert "12.34" not in json.dumps(emitted) and "23.45" not in json.dumps(emitted)


def test_service_entry_configures_logging_and_reports_startup_failure(caplog):
    from services.automotive import automotive_service_cli as cli

    caplog.set_level(logging.INFO)
    with (
        patch.object(cli, "parse_args"),
        patch.object(cli, "configure_logging") as configure,
        patch.object(cli, "_run_service", side_effect=ValueError("private path")),
    ):
        with pytest.raises(ValueError):
            cli.main()
    configure.assert_called_once()
    emitted = events(caplog)
    assert emitted[0]["event"] == "service.failed"
    assert emitted[0]["exception_type"] == "ValueError"
    assert "private" not in json.dumps(emitted)


def test_disconnect_failure_remains_visible_and_close_is_idempotent(caplog):
    caplog.set_level(logging.INFO)
    source = Mock()
    source.disconnect.side_effect = RuntimeError("private device path")
    service = runtime(source)
    service._connected = True
    service._running = True
    with pytest.raises(RuntimeError):
        service.close()
    service.close()
    emitted = events(caplog)
    assert [item["event"] for item in emitted] == ["source.disconnect_failed", "service.stopped"]
    assert "private" not in json.dumps(emitted)
    source.disconnect.assert_called_once()
