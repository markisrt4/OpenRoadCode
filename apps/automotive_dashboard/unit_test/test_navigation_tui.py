import unittest
from datetime import datetime

from apps.automotive_dashboard.navigation_tui import _fields
from controllers.navigation import GpsState, NavigationState
from hardware_io.imu import Vector3


class NavigationTuiTests(unittest.TestCase):
    def test_formats_orientation_and_motion_fields(self) -> None:
        state = NavigationState(
            timestamp=datetime(2026, 1, 2),
            heading_deg=123.456,
            pitch_deg=4.5,
            roll_deg=-6.5,
            acceleration_mps2=Vector3(1.0, 2.0, 2.0),
            linear_acceleration_mps2=Vector3(0.1, 0.2, 0.2),
            angular_velocity_rad_s=Vector3(0.1, 0.2, 0.3),
        )

        fields = dict(_fields(state, gps_enabled=False))

        self.assertEqual(fields["Heading"], "123.46 °")
        self.assertEqual(fields["Raw accel total"], "3.000 m/s²")
        self.assertEqual(fields["Linear accel total"], "0.300 m/s²")
        self.assertEqual(fields["Angular velocity Z"], "0.3000 rad/s")
        self.assertNotIn("GPS fix", fields)

    def test_formats_optional_gps_fields(self) -> None:
        state = NavigationState(
            timestamp=datetime(2026, 1, 2),
            heading_deg=0.0,
            pitch_deg=0.0,
            roll_deg=0.0,
            acceleration_mps2=Vector3(0.0, 0.0, 9.80665),
            linear_acceleration_mps2=Vector3(0.0, 0.0, 0.0),
            angular_velocity_rad_s=Vector3(0.0, 0.0, 0.0),
            gps=GpsState(
                latitude_deg=42.5,
                longitude_deg=-83.0,
                altitude_m=200.0,
                speed_mps=10.0,
                course_deg=180.0,
                fix_mode=3,
                satellites_used=8,
            ),
        )

        fields = dict(_fields(state, gps_enabled=True))

        self.assertEqual(fields["GPS fix"], "3D")
        self.assertEqual(fields["Latitude"], "42.500000 °")
        self.assertEqual(fields["Ground speed"], "10.00 m/s")
        self.assertEqual(fields["Satellites"], "8")

    def test_selects_linear_acceleration_mode(self) -> None:
        state = NavigationState(
            timestamp=datetime(2026, 1, 2),
            heading_deg=0.0,
            pitch_deg=0.0,
            roll_deg=0.0,
            acceleration_mps2=Vector3(0.0, 0.0, 9.80665),
            linear_acceleration_mps2=Vector3(1.0, 0.0, 0.0),
            angular_velocity_rad_s=Vector3(0.0, 0.0, 0.0),
        )

        fields = dict(
            _fields(
                state,
                gps_enabled=False,
                acceleration_mode="linear",
            )
        )

        self.assertEqual(fields["Linear accel X"], "1.000 m/s²")
        self.assertNotIn("Raw accel X", fields)

    def test_shows_waiting_before_first_gps_report(self) -> None:
        fields = dict(_fields(None, gps_enabled=True))

        self.assertEqual(fields["GPS fix"], "Waiting")
        self.assertEqual(fields["Latitude"], "--")


if __name__ == "__main__":
    unittest.main()
