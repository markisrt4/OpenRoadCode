# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for semantic native map requests."""

import math
import unittest

from controllers.map_renderer.map_request_handler import MapRequestHandler
from ui.navigation import GeoPoint, MapMarker, MapMarkerKind


class FakeRenderer:
    def __init__(self) -> None:
        self.cameras: list[tuple[float, float, float, float, float]] = []
        self.poi_focus: list[tuple[str | None, bool]] = []
        self.poi_results: list[dict[str, object]] = []

    def set_camera(
        self,
        latitude: float,
        longitude: float,
        zoom: float,
        bearing: float = 0.0,
        pitch: float = 0.0,
    ) -> None:
        self.cameras.append((latitude, longitude, zoom, bearing, pitch))

    def set_poi_focus(self, category: str | None, enabled: bool = True) -> None:
        self.poi_focus.append((category, enabled))

    def set_poi_results(self, geojson: dict[str, object]) -> None:
        self.poi_results.append(geojson)


class MapRequestHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = FakeRenderer()
        self.follow_changes: list[bool] = []
        self.handler = MapRequestHandler(
            self.renderer,
            center=GeoPoint(math.radians(42.8), math.radians(-83.0)),
            on_follow_changed=self.follow_changes.append,
        )

    def test_zoom_preserves_follow_mode(self) -> None:
        self.handler.request_zoom(14.0)
        self.assertTrue(self.handler.follow_enabled)
        self.assertEqual(self.follow_changes, [])
        self.assertAlmostEqual(self.renderer.cameras[-1][2], 14.0)

    def test_zoom_preserves_manual_mode(self) -> None:
        self.handler.request_follow(False)
        self.follow_changes.clear()
        self.handler.request_zoom(14.0)
        self.assertFalse(self.handler.follow_enabled)
        self.assertEqual(self.follow_changes, [])
        self.assertAlmostEqual(self.renderer.cameras[-1][2], 14.0)

    def test_recenter_restores_follow(self) -> None:
        self.handler.request_follow(False)
        self.handler.update_follow_center(GeoPoint(math.radians(42.9), math.radians(-83.1)))
        self.handler.request_recenter()
        self.assertTrue(self.handler.follow_enabled)
        self.assertEqual(self.follow_changes, [False, True])
        camera = self.renderer.cameras[-1]
        self.assertAlmostEqual(camera[0], 42.9)
        self.assertAlmostEqual(camera[1], -83.1)

    def test_center_on_updates_camera_and_disables_follow(self) -> None:
        self.handler.request_center_on(GeoPoint(math.radians(43.0), math.radians(-83.2)))
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

    def test_follow_bearing_rotates_without_disabling_follow(self) -> None:
        self.handler.update_follow_bearing(math.radians(90.0))
        self.assertTrue(self.handler.follow_enabled)
        self.assertEqual(self.follow_changes, [])
        self.assertAlmostEqual(self.renderer.cameras[-1][3], 90.0)

    def test_follow_bearing_is_ignored_in_manual_mode(self) -> None:
        self.handler.request_follow(False)
        self.renderer.cameras.clear()
        self.handler.update_follow_bearing(math.radians(90.0))
        self.assertEqual(self.renderer.cameras, [])

    def test_follow_camera_updates_center_and_bearing_once(self) -> None:
        point = GeoPoint(math.radians(42.9), math.radians(-83.1))
        self.handler.update_follow_camera(point, math.radians(90.0))
        self.assertTrue(self.handler.follow_enabled)
        self.assertEqual(len(self.renderer.cameras), 1)
        camera = self.renderer.cameras[-1]
        self.assertAlmostEqual(camera[0], 42.9)
        self.assertAlmostEqual(camera[1], -83.1)
        self.assertAlmostEqual(camera[3], 90.0)

    def test_follow_camera_tracks_latest_position_in_manual_mode(self) -> None:
        point = GeoPoint(math.radians(42.9), math.radians(-83.1))
        self.handler.request_follow(False)
        self.renderer.cameras.clear()
        self.handler.update_follow_camera(point, math.radians(90.0))
        self.assertEqual(self.renderer.cameras, [])
        self.handler.request_recenter()
        camera = self.renderer.cameras[-1]
        self.assertAlmostEqual(camera[0], 42.9)
        self.assertAlmostEqual(camera[1], -83.1)

    def _assert_poi_focus_preserves_camera(self, category: str) -> None:
        self.handler = MapRequestHandler(
            self.renderer,
            center=GeoPoint(math.radians(42.8), math.radians(-83.0)),
            zoom_level=12.5,
            pitch_rad=math.radians(45.0),
            follow_enabled=True,
            on_follow_changed=self.follow_changes.append,
        )
        self.handler.request_poi_focus(category)
        self.assertTrue(self.handler.follow_enabled)
        self.assertEqual(self.follow_changes, [])
        self.assertEqual(self.renderer.poi_focus[-1], (category, True))
        self.assertEqual(self.renderer.cameras, [])
        self.assertAlmostEqual(self.handler.zoom_level, 12.5)
        self.assertAlmostEqual(self.handler.pitch_rad, math.radians(45.0))

    def test_fuel_focus_preserves_camera(self) -> None:
        self._assert_poi_focus_preserves_camera("fuel")

    def test_grocery_focus_preserves_camera(self) -> None:
        self._assert_poi_focus_preserves_camera("grocery")

    def test_food_focus_preserves_camera(self) -> None:
        self._assert_poi_focus_preserves_camera("food")

    def test_transit_focus_preserves_camera(self) -> None:
        self._assert_poi_focus_preserves_camera("transit")

    def test_poi_focus_does_not_zoom_out(self) -> None:
        self.handler.request_zoom(16.0)
        self.renderer.cameras.clear()
        self.handler.request_poi_focus("fuel")
        self.assertEqual(self.renderer.poi_focus[-1], ("fuel", True))
        self.assertEqual(self.renderer.cameras, [])

    def test_poi_focus_can_be_toggled_off(self) -> None:
        self.handler.request_poi_focus("fuel")
        self.handler.request_poi_focus("fuel")
        self.assertEqual(self.renderer.poi_focus[-2:], [("fuel", True), ("fuel", False)])

    def test_poi_results_are_serialized_without_changing_camera(self) -> None:
        marker = MapMarker(
            marker_id="poi-1",
            position=GeoPoint(math.radians(42.8), math.radians(-83.0)),
            kind=MapMarkerKind.SEARCH_RESULT,
            label="Lunch",
        )
        self.handler.request_poi_results((marker,), "food")
        self.assertEqual(self.renderer.cameras, [])
        feature = self.renderer.poi_results[-1]["features"][0]
        self.assertEqual(feature["properties"]["name"], "Lunch")
        self.assertEqual(feature["properties"]["category"], "food")
        self.assertAlmostEqual(feature["geometry"]["coordinates"][0], -83.0)
        self.assertAlmostEqual(feature["geometry"]["coordinates"][1], 42.8)


if __name__ == "__main__":
    unittest.main()
