import unittest

from apps.automotive_dashboard.offroad_dashboard import (
    _cardinal_direction,
    _is_capsized,
    _normalize_heading,
    _rotate_screen_point,
    _tilt_severity,
)


class OffroadDashboardTests(unittest.TestCase):
    def test_normalizes_heading(self) -> None:
        self.assertEqual(_normalize_heading(370.0), 10.0)
        self.assertEqual(_normalize_heading(-10.0), 350.0)

    def test_formats_cardinal_directions(self) -> None:
        self.assertEqual(_cardinal_direction(0.0), "N")
        self.assertEqual(_cardinal_direction(90.0), "E")
        self.assertEqual(_cardinal_direction(225.0), "SW")
        self.assertEqual(_cardinal_direction(359.0), "N")

    def test_tilt_severity_uses_configured_thresholds(self) -> None:
        self.assertEqual(
            _tilt_severity(10.0, 10.0, 30.0, 25.0),
            "normal",
        )
        self.assertEqual(
            _tilt_severity(23.0, 10.0, 30.0, 25.0),
            "caution",
        )
        self.assertEqual(
            _tilt_severity(10.0, 26.0, 30.0, 25.0),
            "warning",
        )

    def test_screen_rotation_follows_vehicle_roll(self) -> None:
        point = _rotate_screen_point(
            (10.0, 0.0),
            center_x=100.0,
            center_y=100.0,
            angle_deg=90.0,
        )

        self.assertAlmostEqual(point[0], 100.0)
        self.assertAlmostEqual(point[1], 110.0)

    def test_side_profile_positive_pitch_raises_nose(self) -> None:
        nose = _rotate_screen_point(
            (50.0, 0.0),
            center_x=100.0,
            center_y=100.0,
            angle_deg=-20.0,
        )

        self.assertLess(nose[1], 100.0)

    def test_detects_capsized_attitude(self) -> None:
        self.assertFalse(_is_capsized(10.0, 25.0))
        self.assertFalse(_is_capsized(70.0, 20.0))
        self.assertTrue(_is_capsized(0.0, 170.0))
        self.assertTrue(_is_capsized(130.0, 0.0))


if __name__ == "__main__":
    unittest.main()
