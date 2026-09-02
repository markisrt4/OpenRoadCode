# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Headless tests for CarUI vehicle-gauge application state."""

from apps.carUi.vehicle_gauge_presenter import VehicleGaugePresenter
from messaging.contracts.automotive import VehicleStateData, VehicleStateMessage
from messaging.contracts.common import Timestamp


def _message(source: str = "test-obd") -> VehicleStateMessage:
    return VehicleStateMessage(
        version=1,
        timestamp=Timestamp(seconds=1, nanoseconds=0),
        source=source,
        data=VehicleStateData(
            engine_speed_rad_s=100.0,
            vehicle_speed_m_s=20.0,
            transmission_gear=3,
            throttle_position=0.4,
            accelerator_pedal_position=0.3,
            engine_load=0.5,
            intake_manifold_pressure_pa=120000.0,
            barometric_pressure_pa=101000.0,
            boost_pressure_pa=19000.0,
            mass_air_flow_kg_s=0.02,
            coolant_temperature_k=360.0,
            intake_air_temperature_k=300.0,
            fuel_level=0.75,
            control_voltage_v=13.8,
        ),
    )


def test_initial_snapshot_waits_for_vehicle_telemetry():
    presenter = VehicleGaugePresenter()

    snapshot = presenter.snapshot()

    assert snapshot.vehicle is None
    assert snapshot.error is None
    assert snapshot.received_count == 0
    assert snapshot.status == "Waiting for vehicle telemetry"


def test_vehicle_messages_update_latest_state_and_receive_count():
    presenter = VehicleGaugePresenter()
    first = _message("first")
    second = _message("second")

    presenter.set_vehicle_message(first)
    presenter.set_vehicle_message(second)
    snapshot = presenter.snapshot()

    assert snapshot.vehicle is second
    assert snapshot.received_count == 2
    assert snapshot.status == "Vehicle telemetry: second · 2 messages"
    assert snapshot.vehicle.data.vehicle_speed_m_s == 20.0
    assert snapshot.vehicle.data.transmission_gear == 3
    assert snapshot.vehicle.data.boost_pressure_pa == 19000.0


def test_error_is_reported_and_next_message_clears_it():
    presenter = VehicleGaugePresenter()

    presenter.set_vehicle_error("openroad.vehicle.state", ValueError("bad payload"))
    failed = presenter.snapshot()

    assert failed.error is not None
    assert "ValueError" in failed.status
    assert "bad payload" in failed.status

    presenter.set_vehicle_message(_message())
    recovered = presenter.snapshot()

    assert recovered.error is None
    assert recovered.received_count == 1
    assert recovered.status == "Vehicle telemetry: test-obd · 1 messages"
