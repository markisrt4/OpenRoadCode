# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Fuel-flow helpers for trip calculations."""

from __future__ import annotations

from dataclasses import dataclass

from controllers.automotive.vehicle_state import VehicleState


@dataclass(frozen=True, slots=True)
class FuelModel:
    """Resolve volumetric fuel flow, preferring direct ECU telemetry."""

    stoichiometric_air_fuel_ratio: float = 14.7
    fuel_density_kg_m3: float = 745.0

    def fuel_flow_m3_s(self, state: VehicleState) -> float | None:
        if state.engine_fuel_rate_m3_s is not None:
            return max(0.0, state.engine_fuel_rate_m3_s)
        maf = state.mass_air_flow_kg_s
        if maf is None or maf < 0.0:
            return None
        return maf / self.stoichiometric_air_fuel_ratio / self.fuel_density_kg_m3
