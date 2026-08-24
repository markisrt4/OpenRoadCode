# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Typed decoded representation of the public vehicle-state contract."""

from dataclasses import dataclass

from messaging.contracts.common import Timestamp


@dataclass(frozen=True, slots=True)
class VehicleStateData:
    engine_speed_rad_s: float | None
    vehicle_speed_m_s: float | None
    throttle_position: float | None
    accelerator_pedal_position: float | None
    engine_load: float | None
    intake_manifold_pressure_pa: float | None
    barometric_pressure_pa: float | None
    boost_pressure_pa: float | None
    mass_air_flow_kg_s: float | None
    coolant_temperature_k: float | None
    intake_air_temperature_k: float | None
    fuel_level: float | None
    control_voltage_v: float | None


@dataclass(frozen=True, slots=True)
class VehicleStateMessage:
    version: int
    timestamp: Timestamp
    source: str
    data: VehicleStateData
