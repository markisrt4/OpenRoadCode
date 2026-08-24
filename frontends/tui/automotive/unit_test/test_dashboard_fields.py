# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for terminal dashboard value formatting."""

from datetime import datetime
import math
from types import SimpleNamespace
import unittest

from common.units import UnitSystem
from frontends.tui.automotive.navigation_dashboard_view import navigation_fields
from frontends.tui.automotive.vehicle_dashboard_view import vehicle_fields


class DashboardFieldsTest(unittest.TestCase):
    def test_navigation_fields_accept_structural_snapshot(self) -> None:
        vector = SimpleNamespace(x=1.0, y=2.0, z=2.0)
        state = SimpleNamespace(
            timestamp=datetime.now(),
            heading_deg=90.0,
            pitch_deg=5.0,
            roll_deg=-4.0,
            acceleration_mps2=vector,
            linear_acceleration_mps2=vector,
            angular_velocity_rad_s=vector,
            gps=None,
        )

        fields = dict(
            navigation_fields(
                state,
                gps_enabled=False,
                unit_system=UnitSystem.METRIC,
            )
        )

        self.assertEqual(fields["Heading"], "90.00 °")
        self.assertEqual(fields["Raw accel total"], "3.000 m/s²")

    def test_vehicle_fields_accept_structural_snapshot(self) -> None:
        state = SimpleNamespace(
            timestamp=datetime.now(),
            engine_speed_rad_s=2200.0 * 2.0 * math.pi / 60.0,
            vehicle_speed_m_s=35.5 * 0.44704,
            boost_pressure_pa=2.0 * 6894.757293168,
            coolant_temperature_k=(190.0 - 32.0) * 5.0 / 9.0 + 273.15,
            intake_air_temperature_k=(70.0 - 32.0) * 5.0 / 9.0 + 273.15,
            throttle_position=0.20,
            accelerator_pedal_position=0.18,
            engine_load=0.30,
            intake_manifold_pressure_pa=105_000.0,
            barometric_pressure_pa=100_000.0,
            mass_air_flow_kg_s=0.00825,
            fuel_level=0.75,
            control_voltage_v=13.8,
        )

        fields = dict(vehicle_fields(state))

        self.assertEqual(fields["Engine RPM"], "2200 rpm")
        self.assertEqual(fields["Module voltage"], "13.80 V")

    def test_missing_snapshots_render_unavailable_values(self) -> None:
        self.assertTrue(all(value == "--" for _, value in vehicle_fields(None)))
        self.assertEqual(
            dict(navigation_fields(None, gps_enabled=True))["GPS fix"],
            "Waiting",
        )
