# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Headless tests for the Car TUI vehicle bus cache."""

from datetime import datetime, timezone

import pytest

from apps.carTui.vehicle_bus_state import VehicleBusState
from controllers.automotive import VehicleState
from messaging.contracts.automotive import decode_vehicle_state, encode_vehicle_state


def _message():
    state = VehicleState(
        timestamp=datetime(2026, 8, 22, 12, 34, 56, tzinfo=timezone.utc),
        engine_speed_rad_s=314.1592653589793,
        vehicle_speed_m_s=27.77777777777778,
        throttle_position=0.4,
        accelerator_pedal_position=0.35,
        engine_load=0.5,
        intake_manifold_pressure_pa=135000.0,
        barometric_pressure_pa=101000.0,
        boost_pressure_pa=34000.0,
        mass_air_flow_kg_s=0.012,
        coolant_temperature_k=363.15,
        intake_air_temperature_k=308.15,
        fuel_level=0.75,
        control_voltage_v=13.8,
    )
    return decode_vehicle_state(encode_vehicle_state(state, source="simulated-obd2"))


def test_initial_snapshot_waits_for_vehicle_telemetry():
    cache = VehicleBusState()

    snapshot = cache.snapshot()

    assert snapshot.state is None
    assert snapshot.source is None
    assert snapshot.received_count == 0
    assert snapshot.connected is False
    assert snapshot.status == "Waiting for vehicle telemetry"


def test_vehicle_message_updates_si_state_and_diagnostics():
    cache = VehicleBusState()

    cache.set_vehicle(_message())
    snapshot = cache.snapshot()

    assert snapshot.connected is True
    assert snapshot.source == "simulated-obd2"
    assert snapshot.received_count == 1
    assert snapshot.state is not None
    assert snapshot.state.engine_speed_rad_s == pytest.approx(314.1592653589793)
    assert snapshot.state.vehicle_speed_m_s == pytest.approx(27.77777777777778)
    assert snapshot.state.boost_pressure_pa == pytest.approx(34000.0)
    assert snapshot.state.coolant_temperature_k == pytest.approx(363.15)
    assert "1 messages" in snapshot.status


def test_error_marks_cache_disconnected_until_next_good_message():
    cache = VehicleBusState()
    cache.set_vehicle(_message())

    cache.set_error("openroad.vehicle.state", ValueError("bad payload"))
    failed = cache.snapshot()

    assert failed.connected is False
    assert "ValueError" in failed.status
    assert failed.received_count == 1

    cache.set_vehicle(_message())
    recovered = cache.snapshot()

    assert recovered.connected is True
    assert recovered.received_count == 2
    assert recovered.error is None
