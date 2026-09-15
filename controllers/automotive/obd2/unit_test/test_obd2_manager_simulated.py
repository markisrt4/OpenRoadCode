# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math

import pytest

from controllers.automotive import AutomotiveTelemetryProfile
from controllers.automotive.obd2.obd2_manager import Obd2Manager
from protocols.obd2.simulated_obd2_adapter import SimulatedObd2Adapter


def test_simulated_obd_responses_produce_si_vehicle_state():
    adapter = SimulatedObd2Adapter()
    manager = Obd2Manager(adapter)
    manager.connect()

    state = None
    for _ in range(120):
        state = manager.read_state()
    assert state is not None

    assert state.engine_speed_rad_s == pytest.approx(3000.0 * 2.0 * math.pi / 60.0)
    assert state.vehicle_speed_m_s is None
    assert state.throttle_position == pytest.approx(102.0 / 255.0)
    assert state.accelerator_pedal_position == pytest.approx(89.0 / 255.0)
    assert state.engine_load == pytest.approx(128.0 / 255.0)
    assert state.intake_manifold_pressure_pa == 135000.0
    assert state.barometric_pressure_pa == 101000.0
    assert state.boost_pressure_pa == 34000.0
    assert state.mass_air_flow_kg_s == pytest.approx(0.025)
    assert state.coolant_temperature_k == pytest.approx(363.15)
    assert state.intake_air_temperature_k == pytest.approx(308.15)
    assert state.fuel_level == pytest.approx(191.0 / 255.0)
    assert state.commanded_equivalence_ratio == pytest.approx(1.0)
    assert state.engine_fuel_rate_m3_s == pytest.approx(8.0 / 1000.0 / 3600.0)
    assert state.control_voltage_v == pytest.approx(13.8)

    manager.disconnect()
    assert not adapter.is_connected


def test_scheduler_updates_cached_values_over_multiple_reads():
    adapter = SimulatedObd2Adapter()
    manager = Obd2Manager(adapter)
    manager.connect()

    states = [manager.read_state() for _ in range(24)]

    assert any(state.engine_speed_rad_s is not None for state in states)
    assert any(state.intake_manifold_pressure_pa is not None for state in states)
    assert any(state.throttle_position is not None for state in states)
    assert all(state.vehicle_speed_m_s is None for state in states)



def test_transient_missing_response_preserves_cached_value():
    adapter = SimulatedObd2Adapter()
    manager = Obd2Manager(adapter)
    manager.connect()

    manager.set_telemetry_profile(AutomotiveTelemetryProfile.ECU)

    # Advance until STFT has been sampled into the cache.
    cached = None
    for _ in range(40):
        state = manager.read_state()
        if state.short_term_fuel_trim_bank1 is not None:
            cached = state.short_term_fuel_trim_bank1
            break

    assert cached is not None

    # Simulate a transient empty response on the next STFT poll.
    original = adapter._responses.pop(0x06)
    try:
        for _ in range(40):
            state = manager.read_state()
            assert state.short_term_fuel_trim_bank1 == cached
    finally:
        adapter._responses[0x06] = original

def test_dynamic_simulator_stays_inside_vehicle_ranges():
    adapter = SimulatedObd2Adapter()
    manager = Obd2Manager(adapter)
    manager.connect()

    for _ in range(200):
        adapter.advance()
        state = manager.read_state()

        assert state.vehicle_speed_m_s is None
        if state.throttle_position is not None:
            assert 0.0 <= state.throttle_position <= 1.0
        if state.accelerator_pedal_position is not None:
            assert 0.0 <= state.accelerator_pedal_position <= 1.0
        if state.engine_load is not None:
            assert 0.0 <= state.engine_load <= 1.0
        if state.fuel_level is not None:
            assert 0.0 <= state.fuel_level <= 1.0
        if state.intake_manifold_pressure_pa is not None:
            assert state.intake_manifold_pressure_pa >= 0.0
        if state.barometric_pressure_pa is not None:
            assert state.barometric_pressure_pa == 101000.0
        if state.control_voltage_v is not None:
            assert state.control_voltage_v > 0.0


def test_unsupported_pid_is_none():
    responses = SimulatedObd2Adapter.default_responses()
    responses[0x00] = bytes.fromhex("001A8013")  # clear PID 04 support
    adapter = SimulatedObd2Adapter(responses)
    manager = Obd2Manager(adapter)
    manager.connect()

    state = manager.read_state()

    assert state.engine_load is None


def test_adapter_requires_connection():
    adapter = SimulatedObd2Adapter()

    with pytest.raises(RuntimeError):
        adapter.request(type("Request", (), {"mode": 0x01, "pid": 0x0C})())
