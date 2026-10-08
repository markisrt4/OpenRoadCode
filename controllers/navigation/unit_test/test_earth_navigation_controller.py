"""Verify SI telemetry conversion and follow behavior without a live browser."""

import math
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from controllers.navigation.earth_navigation_controller import EarthNavigationController


class EarthNavigationControllerTest(unittest.TestCase):
    def setUp(self):
        self.bridge, self.camera = Mock(), Mock()
        self.controller = EarthNavigationController(bridge=self.bridge, camera=self.camera, dispatcher=Mock())
        self.controller._on_position(SimpleNamespace(data=SimpleNamespace(
            latitude_rad=math.radians(42), longitude_rad=math.radians(-83), altitude_m=200, pfom_m=6)))
        self.controller._on_motion(SimpleNamespace(data=SimpleNamespace(
            course_rad=math.pi / 2, ground_speed_m_s=12)))

    def test_position_and_motion_are_converted_only_at_browser_boundary(self):
        self.controller.tick()
        self.bridge.push_position.assert_called_once_with(42.0, -83.0,
            altitude_m=200, accuracy_m=6, heading_deg=90.0, speed_m_s=12)
        self.camera.activate_location_tracking.assert_called_once()

    def test_manual_pan_suspends_follow_until_recenter(self):
        self.controller.request_pan_screen(160, 80)
        self.controller.tick()
        self.bridge.push_position.assert_not_called()
        self.camera.pan.assert_called_once_with(right=1.0, up=0.5)
        self.controller.request_recenter()
        self.bridge.push_position.assert_called_once()

    def test_invalid_position_does_not_replay_stale_fix(self):
        self.controller._on_position(SimpleNamespace(data=SimpleNamespace(latitude_rad=None, longitude_rad=None)))
        self.controller.tick()
        self.bridge.push_position.assert_not_called()

    def test_page_not_ready_retries_without_activating_tracking(self):
        self.bridge.install.return_value = False
        self.assertFalse(self.controller.tick())
        self.bridge.push_position.assert_not_called()
        self.camera.activate_location_tracking.assert_not_called()
