# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for cached native-map camera startup."""

import math
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.orcUi.map_camera_runtime import MapCameraRuntime
from controllers.cache import PersistentCache
from controllers.map_renderer.map_request_handler import MapRequestHandler
from controllers.navigation import PositionSnapshotCache, PositionState
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

    def set_poi_focus(self, category: str | None, enabled: bool = True) -> None:
        del category, enabled


class MapCameraCacheTest(unittest.TestCase):
    def test_cached_position_can_seed_camera(self) -> None:
        with TemporaryDirectory() as directory:
            cache = PositionSnapshotCache(PersistentCache(Path(directory)))
            cache.store(
                PositionState(
                    received_at=datetime(2026, 9, 1, 12, 0, 0),
                    latitude_deg=42.8028,
                    longitude_deg=-83.0127,
                    altitude_m=230.0,
                    fix_mode=3,
                    source="navigation-service-android",
                )
            )

            point = MapCameraRuntime._load_cached_center(Path(directory))

            self.assertIsNotNone(point)
            assert point is not None
            self.assertAlmostEqual(42.8028, math.degrees(point.latitude_rad))
            self.assertAlmostEqual(-83.0127, math.degrees(point.longitude_rad))
            self.assertEqual(230.0, point.altitude_m)

    def test_cache_miss_does_not_publish_placeholder_camera(self) -> None:
        renderer = FakeRenderer()
        handler = MapRequestHandler(
            renderer,
            center=GeoPoint(latitude_rad=0.0, longitude_rad=0.0),
            camera_initialized=False,
        )

        handler.refresh_renderer_state()
        handler.request_zoom(14.0)
        handler.update_follow_bearing(math.radians(90.0))

        self.assertEqual([], renderer.cameras)

    def test_first_real_fix_initializes_camera(self) -> None:
        renderer = FakeRenderer()
        handler = MapRequestHandler(
            renderer,
            center=GeoPoint(latitude_rad=0.0, longitude_rad=0.0),
            camera_initialized=False,
        )

        handler.update_follow_camera(
            GeoPoint(
                latitude_rad=math.radians(42.8028),
                longitude_rad=math.radians(-83.0127),
            )
        )

        self.assertEqual(1, len(renderer.cameras))
        self.assertAlmostEqual(42.8028, renderer.cameras[0][0])
        self.assertAlmostEqual(-83.0127, renderer.cameras[0][1])

    def test_zero_zero_is_valid_when_explicitly_initialized(self) -> None:
        renderer = FakeRenderer()
        handler = MapRequestHandler(
            renderer,
            center=GeoPoint(latitude_rad=0.0, longitude_rad=0.0),
            camera_initialized=True,
        )

        handler.refresh_renderer_state()

        self.assertEqual(1, len(renderer.cameras))
        self.assertEqual(0.0, renderer.cameras[0][0])
        self.assertEqual(0.0, renderer.cameras[0][1])


if __name__ == "__main__":
    unittest.main()
