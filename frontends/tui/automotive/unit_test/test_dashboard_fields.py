# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for terminal dashboard value formatting."""

from datetime import datetime
from types import SimpleNamespace
import unittest

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

        fields = dict(navigation_fields(state, gps_enabled=False))

        self.assertEqual(fields["Heading"], "90.00 °")
        self.assertEqual(fields["Raw accel total"], "3.000 m/s²")

    def test_vehicle_fields_accept_structural_snapshot(self) -> None:
        state = SimpleNamespace(
            timestamp=datetime.now(), rpm=2200.0, speed_mph=35.5,
            boost_psi=2.0, coolant_temp_f=190.0, intake_temp_f=70.0,
            throttle_pct=20.0, accelerator_pedal_pct=18.0,
            engine_load_pct=30.0, map_kpa=105, baro_kpa=100,
            maf_gps=8.25, fuel_level_pct=75.0, control_voltage=13.8,
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
