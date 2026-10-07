# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest
from unittest.mock import patch

from hardware_io.camera.v4l2_camera_controls import (
    DAY_PROFILE,
    LOW_LIGHT_PROFILE,
    V4L2CameraProfile,
    V4L2CameraProfileController,
)
from hardware_io.camera.camera_controls_if import CameraProfile


class V4L2CameraProfileTest(unittest.TestCase):
    def test_day_profile_uses_camera_auto_exposure(self) -> None:
        self.assertEqual(DAY_PROFILE.auto_exposure, 0)
        self.assertIsNone(DAY_PROFILE.exposure_time_absolute)
        self.assertEqual(DAY_PROFILE.power_line_frequency, 2)

    def test_low_light_profile_uses_supported_auto_exposure(self) -> None:
        self.assertEqual(LOW_LIGHT_PROFILE.auto_exposure, 0)
        self.assertIsNone(LOW_LIGHT_PROFILE.exposure_time_absolute)
        self.assertLessEqual(LOW_LIGHT_PROFILE.gain, 10)

    def test_profile_values_are_stable(self) -> None:
        self.assertEqual(V4L2CameraProfile.DAY.value, "day")
        self.assertEqual(V4L2CameraProfile.LOW_LIGHT.value, "low_light")

    @patch("hardware_io.camera.v4l2_camera_controls.subprocess.run")
    def test_probe_rejects_profile_when_exact_menu_value_is_absent(self, run) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = """
                     auto_exposure 0x009a0901 (menu) : min=0 max=3 default=3 value=3
                                1: Manual Mode
                                3: Aperture Priority Mode
                               gain 0x00980913 (int) : min=0 max=255 step=1 default=0 value=0
                              gamma 0x00980910 (int) : min=100 max=500 step=1 default=100 value=100
             backlight_compensation 0x0098091c (int) : min=0 max=1 step=1 default=0 value=0
                power_line_frequency 0x00980918 (menu) : min=0 max=2 default=2 value=2
                                0: Disabled
                                1: 50 Hz
                                2: 60 Hz
"""
        controls = V4L2CameraProfileController()

        self.assertEqual(controls.probe_supported_profiles(), frozenset())

    @patch("hardware_io.camera.v4l2_camera_controls.subprocess.run")
    def test_probe_accepts_profiles_when_controls_and_values_exist(self, run) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = """
                     auto_exposure 0x009a0901 (menu) : min=0 max=3 default=0 value=0
                                0: Auto Mode
                               gain 0x00980913 (int) : min=0 max=255 step=1 default=0 value=0
                              gamma 0x00980910 (int) : min=100 max=500 step=1 default=100 value=100
             backlight_compensation 0x0098091c (int) : min=0 max=1 step=1 default=0 value=0
                power_line_frequency 0x00980918 (menu) : min=0 max=2 default=2 value=2
                                2: 60 Hz
"""
        controls = V4L2CameraProfileController()

        self.assertEqual(
            controls.probe_supported_profiles(),
            frozenset((CameraProfile.DAY, CameraProfile.LOW_LIGHT)),
        )


if __name__ == "__main__":
    unittest.main()
