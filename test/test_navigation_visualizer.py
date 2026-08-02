import unittest

from apps.automotive_dashboard.navigation_visualizer import (
    _build_jeep_model,
    _rotate_point,
)


class NavigationVisualizerTests(unittest.TestCase):
    def test_heading_rotates_forward_axis_around_z(self) -> None:
        rotated = _rotate_point(
            (1.0, 0.0, 0.0),
            heading_deg=90.0,
            pitch_deg=0.0,
            roll_deg=0.0,
        )

        self.assertAlmostEqual(rotated[0], 0.0)
        self.assertAlmostEqual(rotated[1], 1.0)
        self.assertAlmostEqual(rotated[2], 0.0)

    def test_pitch_rotates_forward_axis(self) -> None:
        rotated = _rotate_point(
            (1.0, 0.0, 0.0),
            heading_deg=0.0,
            pitch_deg=90.0,
            roll_deg=0.0,
        )

        self.assertAlmostEqual(rotated[0], 0.0)
        self.assertAlmostEqual(rotated[1], 0.0)
        self.assertAlmostEqual(rotated[2], 1.0)

    def test_positive_roll_lowers_right_side(self) -> None:
        rotated = _rotate_point(
            (0.0, 1.0, 0.0),
            heading_deg=0.0,
            pitch_deg=0.0,
            roll_deg=90.0,
        )

        self.assertAlmostEqual(rotated[0], 0.0)
        self.assertAlmostEqual(rotated[1], 0.0)
        self.assertAlmostEqual(rotated[2], -1.0)

    def test_jeep_model_contains_body_and_wheels(self) -> None:
        model = _build_jeep_model()

        self.assertGreater(len(model.points), 50)
        self.assertGreater(len(model.body_edges), 30)
        self.assertEqual(len(model.wheel_edges), 48)


if __name__ == "__main__":
    unittest.main()
