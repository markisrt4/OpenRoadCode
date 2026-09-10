# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest

from controllers.computer_vision.camera_frame_processor import CameraMode


class CameraModeTest(unittest.TestCase):
    def test_values_are_stable(self) -> None:
        self.assertEqual(CameraMode.AUTO.value, "auto")
        self.assertEqual(CameraMode.DAY.value, "day")
        self.assertEqual(CameraMode.LOW_LIGHT.value, "low_light")


if __name__ == "__main__":
    unittest.main()
