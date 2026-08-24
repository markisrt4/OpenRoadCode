# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math

import pytest

from controllers.automotive.obd2.obd2_manager import Obd2Manager
from protocols.obd2.simulated_obd2_adapter import SimulatedObd2Adapter


def test_simulated_obd_responses_produce_si_vehicle_state():
    adapter = SimulatedObd2Adapter()
    manager = Obd2Manager(adapter)
    manager.connect()

    state = manager.read_state()

    assert state.engine_speed_rad_s == pytest.approx(3000.0 * 2.0 * math.pi / 60.0)
    assert state.vehicle_speed_m_s == pytest.approx(100.0 / 3.6)
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
    assert state.control_voltage_v == pytest.approx(13.8)

    manager.disconnect()
    assert not adapter.is_connected


def test_advance_changes_raw_pid_data_and_decoded_state():
    adapter = SimulatedObd2Adapter()
    manager = Obd2Manager(adapter)
    manager.connect()

    before = manager.read_state()
    rpm_bytes_before = adapter._responses[0x0C]
    speed_bytes_before = adapter._responses[0x0D]

    adapter.advance()
    after = manager.read_state()

    assert adapter._responses[0x0C] != rpm_bytes_before
    assert adapter._responses[0x0D] != speed_bytes_before
    assert after.engine_speed_rad_s != before.engine_speed_rad_s
    assert after.vehicle_speed_m_s != before.vehicle_speed_m_s
    assert after.throttle_position != before.throttle_position
    assert after.intake_manifold_pressure_pa != before.intake_manifold_pressure_pa
    assert after.boost_pressure_pa == pytest.approx(
        after.intake_manifold_pressure_pa - after.barometric_pressure_pa
    )


def test_dynamic_simulator_stays_inside_vehicle_ranges():
    adapter = SimulatedObd2Adapter()
    manager = Obd2Manager(adapter)
    manager.connect()

    for _ in range(200):
        adapter.advance()
        state = manager.read_state()

        assert 0.0 <= state.vehicle_speed_m_s <= 255.0 / 3.6
        assert 0.0 <= state.throttle_position <= 1.0
        assert 0.0 <= state.accelerator_pedal_position <= 1.0
        assert 0.0 <= state.engine_load <= 1.0
        assert 0.0 <= state.fuel_level <= 1.0
        assert state.intake_manifold_pressure_pa >= 0.0
        assert state.barometric_pressure_pa == 101000.0
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
