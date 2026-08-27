# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for hardware-free navigation simulation."""

import unittest

from controllers.navigation import SimulatedNavigationController


class SimulatedNavigationControllerTest(unittest.TestCase):
    def test_generates_changing_motion_and_valid_position(self) -> None:
        controller = SimulatedNavigationController()
        controller.start()

        first = controller.read_state()
        second = controller.read_state()

        self.assertNotEqual(first.heading_deg, second.heading_deg)
        self.assertNotEqual(first.roll_deg, second.roll_deg)
        self.assertIsNotNone(second.position)
        self.assertTrue(second.position.has_fix)  # type: ignore[union-attr]
        self.assertEqual(second.position.source, "simulation")  # type: ignore[union-attr]
        self.assertIsNotNone(second.ground_motion)
        self.assertIsNotNone(second.ground_motion.speed_mps)  # type: ignore[union-attr]
        self.assertEqual(second.ground_motion.source, "simulation")  # type: ignore[union-attr]

    def test_supports_calibration_and_heading_reset(self) -> None:
        controller = SimulatedNavigationController()
        controller.start()

        calibration = controller.calibrate_stationary(sample_count=25)
        controller.reset_heading()
        state = controller.read_state()

        self.assertEqual(calibration.sample_count, 25)
        self.assertAlmostEqual(state.heading_deg, 1.5)


if __name__ == "__main__":
    unittest.main()
