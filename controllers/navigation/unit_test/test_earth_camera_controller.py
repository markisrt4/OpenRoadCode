# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest
from unittest.mock import Mock, PropertyMock

from controllers.navigation.earth_camera_controller import EarthCameraController
from controllers.navigation.earth_camera_controller_if import EarthCameraView


class EarthCameraControllerTest(unittest.TestCase):
    def test_uses_first_available_controller_that_succeeds(self) -> None:
        cdp = Mock()
        type(cdp).name = PropertyMock(return_value="CDP")
        cdp.available.return_value = True
        cdp.set_view.return_value = False
        dom = Mock()
        type(dom).name = PropertyMock(return_value="DOM")
        dom.available.return_value = True
        dom.set_view.return_value = True
        input_controller = Mock()
        controller = EarthCameraController((cdp, dom, input_controller))
        view = EarthCameraView(42.819, -83.018, heading_deg=90.0, tilt_deg=60.0)

        self.assertTrue(controller.set_view(view))
        cdp.set_view.assert_called_once_with(view)
        dom.set_view.assert_called_once_with(view)
        input_controller.set_view.assert_not_called()
        self.assertEqual(controller.active_controller_name, "DOM")

    def test_controller_exception_falls_through(self) -> None:
        cdp = Mock()
        cdp.available.side_effect = RuntimeError("browser changed")
        fallback = Mock()
        type(fallback).name = PropertyMock(return_value="INPUT")
        fallback.available.return_value = True
        fallback.set_view.return_value = True
        controller = EarthCameraController((cdp, fallback))

        self.assertTrue(controller.set_view(EarthCameraView(42.0, -83.0)))
        self.assertEqual(controller.active_controller_name, "INPUT")

    def test_reports_failure_when_no_controller_can_apply_view(self) -> None:
        unavailable = Mock()
        unavailable.available.return_value = False
        controller = EarthCameraController((unavailable,))

        self.assertFalse(controller.set_view(EarthCameraView(42.0, -83.0)))
        self.assertIsNone(controller.active_controller_name)


if __name__ == "__main__":
    unittest.main()
