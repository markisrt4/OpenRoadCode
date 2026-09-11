# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Fuel-flow helpers for trip calculations."""

from __future__ import annotations

import math
from dataclasses import dataclass

from controllers.automotive.vehicle_state import VehicleState

SPECIFIC_GAS_CONSTANT_AIR_J_KG_K = 287.05


@dataclass(frozen=True, slots=True)
class FuelModel:
    """Resolve volumetric fuel flow using the best available telemetry.

    Preference order is direct ECU fuel rate, MAF-derived flow, then a
    configurable speed-density estimate using MAP, RPM, and intake temperature.
    """

    stoichiometric_air_fuel_ratio: float = 14.7
    fuel_density_kg_m3: float = 745.0
    engine_displacement_m3: float | None = None
    volumetric_efficiency: float = 0.85

    def __post_init__(self) -> None:
        if self.stoichiometric_air_fuel_ratio <= 0.0:
            raise ValueError("stoichiometric_air_fuel_ratio must be positive")
        if self.fuel_density_kg_m3 <= 0.0:
            raise ValueError("fuel_density_kg_m3 must be positive")
        if self.engine_displacement_m3 is not None and self.engine_displacement_m3 <= 0.0:
            raise ValueError("engine_displacement_m3 must be positive")
        if not 0.0 < self.volumetric_efficiency <= 1.5:
            raise ValueError("volumetric_efficiency must be in range 0..1.5")

    def fuel_flow_m3_s(self, state: VehicleState) -> float | None:
        """Return fuel volume flow in cubic metres per second."""
        if state.engine_fuel_rate_m3_s is not None:
            return max(0.0, state.engine_fuel_rate_m3_s)

        maf = state.mass_air_flow_kg_s
        if maf is not None and maf >= 0.0:
            return self._fuel_flow_from_air_mass(maf)

        estimated_maf = self._speed_density_air_mass_flow_kg_s(state)
        if estimated_maf is None:
            return None
        return self._fuel_flow_from_air_mass(estimated_maf)

    def _fuel_flow_from_air_mass(self, air_mass_flow_kg_s: float) -> float:
        fuel_mass_flow_kg_s = (
            air_mass_flow_kg_s / self.stoichiometric_air_fuel_ratio
        )
        return fuel_mass_flow_kg_s / self.fuel_density_kg_m3

    def _speed_density_air_mass_flow_kg_s(
        self,
        state: VehicleState,
    ) -> float | None:
        displacement = self.engine_displacement_m3
        map_pa = state.intake_manifold_pressure_pa
        temperature_k = state.intake_air_temperature_k
        omega_rad_s = state.engine_speed_rad_s

        if (
            displacement is None
            or map_pa is None
            or temperature_k is None
            or omega_rad_s is None
            or map_pa < 0.0
            or temperature_k <= 0.0
            or omega_rad_s < 0.0
        ):
            return None

        # Four-stroke engines ingest one displacement volume every two
        # crankshaft revolutions. Ideal-gas density converts manifold volume
        # flow to air mass flow; VE accounts for real cylinder filling.
        return (
            map_pa
            * displacement
            * self.volumetric_efficiency
            * omega_rad_s
            / (
                4.0
                * math.pi
                * SPECIFIC_GAS_CONSTANT_AIR_J_KG_K
                * temperature_k
            )
        )
