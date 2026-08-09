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
        self.assertTrue(second.gps.has_fix)
        self.assertIsNotNone(second.gps.speed_mps)
        self.assertEqual(second.gps.source, "simulation")

    def test_supports_calibration_and_heading_reset(self) -> None:
        controller = SimulatedNavigationController()
        controller.start()

        calibration = controller.calibrate_stationary(sample_count=25)
        controller.reset_heading()
        state = controller.read_state()

        self.assertEqual(calibration.sample_count, 25)
        self.assertAlmostEqual(state.heading_deg, 1.5)
