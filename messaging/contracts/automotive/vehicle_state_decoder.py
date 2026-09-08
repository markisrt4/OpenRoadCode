# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Decode the public vehicle-state wire contract."""

from collections.abc import Mapping
from typing import Any

from messaging.contracts.common import decode_timestamp

from .vehicle_state_message import VehicleStateData, VehicleStateMessage
from .vehicle_state_validator import validate_vehicle_state


def decode_vehicle_state(payload: Mapping[str, Any]) -> VehicleStateMessage:
    """Validate and decode a vehicle-state payload into SI-native message types."""
    validate_vehicle_state(payload)
    data = payload["data"]

    return VehicleStateMessage(
        version=payload["version"],
        timestamp=decode_timestamp(payload["timestamp"]),
        source=payload["source"],
        data=VehicleStateData(
            engine_speed_rad_s=data["engine_speed_rad_s"],
            vehicle_speed_m_s=data["vehicle_speed_m_s"],
            transmission_gear=data["transmission_gear"],
            throttle_position=data["throttle_position"],
            accelerator_pedal_position=data["accelerator_pedal_position"],
            engine_load=data["engine_load"],
            intake_manifold_pressure_pa=data["intake_manifold_pressure_pa"],
            barometric_pressure_pa=data["barometric_pressure_pa"],
            boost_pressure_pa=data["boost_pressure_pa"],
            mass_air_flow_kg_s=data["mass_air_flow_kg_s"],
            coolant_temperature_k=data["coolant_temperature_k"],
            intake_air_temperature_k=data["intake_air_temperature_k"],
            fuel_level=data["fuel_level"],
            control_voltage_v=data["control_voltage_v"],
        ),
    )
