# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for automotive fuel-flow resolution."""

from datetime import datetime, timezone
import math

import pytest

from controllers.automotive.fuel_model import FuelModel
from controllers.automotive.vehicle_state import VehicleState


NOW = datetime(2026, 9, 11, tzinfo=timezone.utc)


def test_direct_fuel_rate_has_highest_priority() -> None:
    model = FuelModel(engine_displacement_m3=0.0016)
    state = VehicleState(
        timestamp=NOW,
        engine_fuel_rate_m3_s=3.0e-6,
        mass_air_flow_kg_s=0.02,
        intake_manifold_pressure_pa=120000.0,
        intake_air_temperature_k=300.0,
        engine_speed_rad_s=3000.0 * 2.0 * math.pi / 60.0,
    )

    assert model.fuel_flow_m3_s(state) == pytest.approx(3.0e-6)


def test_maf_is_used_before_speed_density() -> None:
    model = FuelModel(engine_displacement_m3=0.0016)
    state = VehicleState(
        timestamp=NOW,
        mass_air_flow_kg_s=0.0147,
        intake_manifold_pressure_pa=120000.0,
        intake_air_temperature_k=300.0,
        engine_speed_rad_s=3000.0 * 2.0 * math.pi / 60.0,
    )

    expected = 0.0147 / 14.7 / 745.0
    assert model.fuel_flow_m3_s(state) == pytest.approx(expected)


def test_speed_density_estimates_flow_from_map_rpm_and_iat() -> None:
    model = FuelModel(
        engine_displacement_m3=0.0016,
        volumetric_efficiency=0.85,
    )
    state = VehicleState(
        timestamp=NOW,
        intake_manifold_pressure_pa=100000.0,
        intake_air_temperature_k=300.0,
        engine_speed_rad_s=3000.0 * 2.0 * math.pi / 60.0,
    )

    air_mass_flow = (
        100000.0
        * 0.0016
        * 0.85
        * state.engine_speed_rad_s
        / (4.0 * math.pi * 287.05 * 300.0)
    )
    expected = air_mass_flow / 14.7 / 745.0

    assert model.fuel_flow_m3_s(state) == pytest.approx(expected)



def test_commanded_equivalence_ratio_increases_fuel_when_rich() -> None:
    model = FuelModel(
        engine_displacement_m3=0.0016,
        volumetric_efficiency=0.85,
    )
    stoich_state = VehicleState(
        timestamp=NOW,
        intake_manifold_pressure_pa=120000.0,
        intake_air_temperature_k=300.0,
        engine_speed_rad_s=3500.0 * 2.0 * math.pi / 60.0,
        commanded_equivalence_ratio=1.0,
    )
    rich_state = VehicleState(
        timestamp=NOW,
        intake_manifold_pressure_pa=120000.0,
        intake_air_temperature_k=300.0,
        engine_speed_rad_s=3500.0 * 2.0 * math.pi / 60.0,
        commanded_equivalence_ratio=0.80,
    )

    stoich_flow = model.fuel_flow_m3_s(stoich_state)
    rich_flow = model.fuel_flow_m3_s(rich_state)

    assert stoich_flow is not None
    assert rich_flow == pytest.approx(stoich_flow / 0.80)

def test_speed_density_requires_configured_displacement() -> None:
    model = FuelModel()
    state = VehicleState(
        timestamp=NOW,
        intake_manifold_pressure_pa=100000.0,
        intake_air_temperature_k=300.0,
        engine_speed_rad_s=3000.0 * 2.0 * math.pi / 60.0,
    )

    assert model.fuel_flow_m3_s(state) is None
