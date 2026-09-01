# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation model for vehicle telemetry shown by orcUi."""

from __future__ import annotations

import math
from dataclasses import dataclass

from messaging.contracts.automotive import VehicleStateData


RPM_PER_RAD_S = 60.0 / (2.0 * math.pi)
MPH_PER_MPS = 2.2369362920544
PSI_PER_PA = 0.00014503773773020923


@dataclass(frozen=True, slots=True)
class VehiclePresentationState:
    """Vehicle telemetry converted into driver-facing units."""

    speed_mph: float | None = None
    engine_speed_rpm: float | None = None
    boost_psi: float | None = None
    coolant_temperature_f: float | None = None
    intake_air_temperature_f: float | None = None
    throttle_percent: float | None = None
    engine_load_percent: float | None = None
    fuel_percent: float | None = None
    control_voltage_v: float | None = None


class VehiclePresenter:
    """Convert the SI-normalized automotive contract for cockpit display."""

    @staticmethod
    def present(state: VehicleStateData) -> VehiclePresentationState:
        return VehiclePresentationState(
            speed_mph=(
                None
                if state.vehicle_speed_m_s is None
                else state.vehicle_speed_m_s * MPH_PER_MPS
            ),
            engine_speed_rpm=(
                None
                if state.engine_speed_rad_s is None
                else state.engine_speed_rad_s * RPM_PER_RAD_S
            ),
            boost_psi=(
                None
                if state.boost_pressure_pa is None
                else state.boost_pressure_pa * PSI_PER_PA
            ),
            coolant_temperature_f=(
                None
                if state.coolant_temperature_k is None
                else (state.coolant_temperature_k - 273.15) * 9.0 / 5.0 + 32.0
            ),
            intake_air_temperature_f=(
                None
                if state.intake_air_temperature_k is None
                else (state.intake_air_temperature_k - 273.15) * 9.0 / 5.0 + 32.0
            ),
            throttle_percent=(
                None
                if state.throttle_position is None
                else state.throttle_position * 100.0
            ),
            engine_load_percent=(
                None if state.engine_load is None else state.engine_load * 100.0
            ),
            fuel_percent=(
                None if state.fuel_level is None else state.fuel_level * 100.0
            ),
            control_voltage_v=state.control_voltage_v,
        )
