# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class VehicleState:
    """Immutable SI-normalized snapshot of decoded vehicle telemetry.

    Values that were unsupported or unavailable during the latest poll are
    ``None``. Fractions use the range 0.0 through 1.0. ``transmission_gear``
    uses -1 for reverse, 0 for neutral, and 1 through 6 for forward gears.
    ``None`` means unknown or indeterminate, such as during a shift.
    """

    timestamp: datetime

    engine_speed_rad_s: float | None = None
    vehicle_speed_m_s: float | None = None
    transmission_gear: int | None = None

    throttle_position: float | None = None
    commanded_throttle_position: float | None = None
    accelerator_pedal_position: float | None = None
    engine_load: float | None = None
    absolute_engine_load: float | None = None

    fuel_system_status_1: int | None = None
    fuel_system_status_2: int | None = None
    short_term_fuel_trim_bank1: float | None = None
    long_term_fuel_trim_bank1: float | None = None
    ignition_timing_advance_deg: float | None = None

    intake_manifold_pressure_pa: float | None = None
    barometric_pressure_pa: float | None = None
    boost_pressure_pa: float | None = None
    mass_air_flow_kg_s: float | None = None

    coolant_temperature_k: float | None = None
    intake_air_temperature_k: float | None = None

    fuel_level: float | None = None
    fuel_rail_pressure_pa: float | None = None
    commanded_equivalence_ratio: float | None = None
    measured_equivalence_ratio: float | None = None
    engine_fuel_rate_m3_s: float | None = None
    control_voltage_v: float | None = None
