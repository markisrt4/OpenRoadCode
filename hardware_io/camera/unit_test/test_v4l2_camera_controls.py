# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest

from hardware_io.camera.v4l2_camera_controls import (
    DAY_PROFILE,
    LOW_LIGHT_PROFILE,
    V4L2CameraProfile,
)


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


if __name__ == "__main__":
    unittest.main()
