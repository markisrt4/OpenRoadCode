# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for semantic native map requests."""

import math
import unittest

from controllers.map_renderer.map_request_handler import MapRequestHandler
from ui.navigation import GeoPoint


class FakeRenderer:
    def __init__(self) -> None:
        self.cameras: list[tuple[float, float, float, float, float]] = []

    def set_camera(
        self,
        latitude: float,
        longitude: float,
        zoom: float,
        bearing: float = 0.0,
        pitch: float = 0.0,
    ) -> None:
        self.cameras.append((latitude, longitude, zoom, bearing, pitch))


class MapRequestHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = FakeRenderer()
        self.follow_changes: list[bool] = []
        self.handler = MapRequestHandler(
            self.renderer,
            center=GeoPoint(math.radians(42.8), math.radians(-83.0)),
            on_follow_changed=self.follow_changes.append,
        )

    def test_manual_camera_request_disables_follow(self) -> None:
        self.handler.request_zoom(14.0)

        self.assertFalse(self.handler.follow_enabled)
        self.assertEqual(self.follow_changes, [False])
        self.assertAlmostEqual(self.renderer.cameras[-1][2], 14.0)

    def test_recenter_restores_follow(self) -> None:
        self.handler.request_follow(False)
        self.handler.update_follow_center(
            GeoPoint(math.radians(42.9), math.radians(-83.1))
        )
        self.handler.request_recenter()

        self.assertTrue(self.handler.follow_enabled)
        self.assertEqual(self.follow_changes, [False, True])
        camera = self.renderer.cameras[-1]
        self.assertAlmostEqual(camera[0], 42.9)
        self.assertAlmostEqual(camera[1], -83.1)

    def test_center_on_updates_camera_and_disables_follow(self) -> None:
        self.handler.request_center_on(
            GeoPoint(math.radians(43.0), math.radians(-83.2))
        )

        self.assertFalse(self.handler.follow_enabled)
        camera = self.renderer.cameras[-1]
        self.assertAlmostEqual(camera[0], 43.0)
        self.assertAlmostEqual(camera[1], -83.2)

    def test_pan_north_updates_camera_and_disables_follow(self) -> None:
        self.handler.request_pan(north_m=1000.0, east_m=0.0)

        self.assertFalse(self.handler.follow_enabled)
        self.assertEqual(self.follow_changes, [False])
        camera = self.renderer.cameras[-1]
        self.assertGreater(camera[0], 42.8)
        self.assertAlmostEqual(camera[1], -83.0)

    def test_pan_east_updates_camera_and_disables_follow(self) -> None:
        self.handler.request_pan(north_m=0.0, east_m=1000.0)

        self.assertFalse(self.handler.follow_enabled)
        self.assertEqual(self.follow_changes, [False])
        camera = self.renderer.cameras[-1]
        self.assertAlmostEqual(camera[0], 42.8)
        self.assertGreater(camera[1], -83.0)


if __name__ == "__main__":
    unittest.main()
