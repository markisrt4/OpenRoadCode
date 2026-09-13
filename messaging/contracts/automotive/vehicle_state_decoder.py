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
            commanded_throttle_position=data.get("commanded_throttle_position"),
            accelerator_pedal_position=data["accelerator_pedal_position"],
            engine_load=data["engine_load"],
            absolute_engine_load=data.get("absolute_engine_load"),
            fuel_system_status_1=data.get("fuel_system_status_1"),
            fuel_system_status_2=data.get("fuel_system_status_2"),
            short_term_fuel_trim_bank1=data.get("short_term_fuel_trim_bank1"),
            long_term_fuel_trim_bank1=data.get("long_term_fuel_trim_bank1"),
            ignition_timing_advance_deg=data.get("ignition_timing_advance_deg"),
            intake_manifold_pressure_pa=data["intake_manifold_pressure_pa"],
            barometric_pressure_pa=data["barometric_pressure_pa"],
            boost_pressure_pa=data["boost_pressure_pa"],
            mass_air_flow_kg_s=data["mass_air_flow_kg_s"],
            coolant_temperature_k=data["coolant_temperature_k"],
            intake_air_temperature_k=data["intake_air_temperature_k"],
            fuel_level=data["fuel_level"],
            fuel_rail_pressure_pa=data.get("fuel_rail_pressure_pa"),
            commanded_equivalence_ratio=data.get("commanded_equivalence_ratio"),
            measured_equivalence_ratio=data.get("measured_equivalence_ratio"),
            engine_fuel_rate_m3_s=data.get("engine_fuel_rate_m3_s"),
            control_voltage_v=data["control_voltage_v"],
        ),
    )
