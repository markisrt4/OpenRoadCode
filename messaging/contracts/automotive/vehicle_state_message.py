# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Typed decoded representation of the public vehicle-state contract."""

from dataclasses import dataclass

from messaging.contracts.common import Timestamp


@dataclass(frozen=True, slots=True)
class VehicleStateData:
    engine_speed_rad_s: float | None
    vehicle_speed_m_s: float | None
    transmission_gear: int | None
    throttle_position: float | None
    commanded_throttle_position: float | None
    accelerator_pedal_position: float | None
    engine_load: float | None
    absolute_engine_load: float | None
    fuel_system_status_1: int | None
    fuel_system_status_2: int | None
    short_term_fuel_trim_bank1: float | None
    long_term_fuel_trim_bank1: float | None
    ignition_timing_advance_deg: float | None
    intake_manifold_pressure_pa: float | None
    barometric_pressure_pa: float | None
    boost_pressure_pa: float | None
    mass_air_flow_kg_s: float | None
    coolant_temperature_k: float | None
    intake_air_temperature_k: float | None
    fuel_level: float | None
    fuel_rail_pressure_pa: float | None
    commanded_equivalence_ratio: float | None
    measured_equivalence_ratio: float | None
    engine_fuel_rate_m3_s: float | None
    control_voltage_v: float | None


@dataclass(frozen=True, slots=True)
class VehicleStateMessage:
    version: int
    timestamp: Timestamp
    source: str
    data: VehicleStateData
