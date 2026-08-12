# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for alternate navigation controller implementations."""

from __future__ import annotations

import unittest
from datetime import datetime

from hardware_io.imu import Vector3

from controllers.navigation import (
    GpsState,
    NavigationController,
    NavigationControllerIf,
    NavigationControllerStub,
    NavigationState,
    UnconfiguredNavigationController,
)


def _state() -> NavigationState:
    zero = Vector3(0.0, 0.0, 0.0)
    return NavigationState(
        timestamp=datetime(2026, 1, 2, 3, 4, 5),
        heading_deg=10.0,
        pitch_deg=2.0,
        roll_deg=3.0,
        acceleration_mps2=Vector3(0.0, 0.0, 9.80665),
        linear_acceleration_mps2=zero,
        angular_velocity_rad_s=zero,
    )


class NavigationControllerContractTests(unittest.TestCase):
    def test_all_implementations_derive_from_interface(self) -> None:
        for controller_type in (
            NavigationController,
            NavigationControllerStub,
            UnconfiguredNavigationController,
        ):
            with self.subTest(controller_type=controller_type):
                self.assertTrue(
                    issubclass(controller_type, NavigationControllerIf)
                )
                self.assertFalse(controller_type.__abstractmethods__)


class NavigationControllerStubTests(unittest.TestCase):
    def test_returns_deterministic_state(self) -> None:
        expected = _state()
        controller = NavigationControllerStub(expected)

        controller.start()

        self.assertIs(controller.read_state(), expected)
        self.assertIs(controller.read_state(), expected)
        self.assertTrue(controller.is_available)
        self.assertIsNone(controller.status_message)

    def test_updates_heading_gps_and_calibration(self) -> None:
        controller = NavigationControllerStub(_state())
        gps = GpsState(
            latitude_deg=42.5,
            longitude_deg=-83.0,
            fix_mode=3,
        )

        controller.start()
        controller.reset_heading(370.0)
        controller.update_gps_state(gps)
        calibration = controller.calibrate_stationary(
            sample_count=12,
            sample_interval_s=0.0,
        )
        state = controller.read_state()

        self.assertEqual(state.heading_deg, 10.0)
        self.assertEqual(state.gps, gps)
        self.assertEqual(calibration.sample_count, 12)
        self.assertEqual(controller.calibration, calibration)

    def test_requires_start_for_stateful_operations(self) -> None:
        controller = NavigationControllerStub()

        with self.assertRaises(RuntimeError):
            controller.read_state()
        with self.assertRaises(RuntimeError):
            controller.reset_heading()
        with self.assertRaises(RuntimeError):
            controller.calibrate_stationary()


class UnconfiguredNavigationControllerTests(unittest.TestCase):
    def test_reports_unavailable_reason(self) -> None:
        controller = UnconfiguredNavigationController("IMU disabled")

        self.assertFalse(controller.is_available)
        self.assertFalse(controller.is_started)
        self.assertEqual(controller.status_message, "IMU disabled")
        self.assertIsNone(controller.calibration)

    def test_navigation_operations_raise_reason(self) -> None:
        controller = UnconfiguredNavigationController("IMU disabled")
        operations = (
            controller.start,
            controller.reset_heading,
            controller.calibrate_stationary,
            lambda: controller.update_gps_state(GpsState()),
            controller.read_state,
        )

        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(RuntimeError, "IMU disabled"):
                    operation()

        controller.stop()


if __name__ == "__main__":
    unittest.main()
