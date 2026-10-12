# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for the native map renderer UI adapter."""

import math
import unittest

from frontends.common.map_renderer_ui import MapRendererUi
from ui.navigation import (
    GeoPoint,
    MapMarker,
    MapMarkerKind,
    MapRequestHandlerStub,
    MapState,
    MapViewport,
    RouteGeometry,
)


class FakeRenderer:
    def __init__(self) -> None:
        self.camera: tuple[float, float, float, float, float] | None = None
        self.position: tuple[float, float] | None = None
        self.route: dict[str, object] | None = None
        self.heading: float | None = None

    def set_camera(self, latitude: float, longitude: float, zoom: float,
                   bearing: float = 0.0, pitch: float = 0.0) -> None:
        self.camera = (latitude, longitude, zoom, bearing, pitch)

    def set_position(self, latitude: float, longitude: float, *,
                     heading_deg: float | None = None) -> None:
        self.position = (latitude, longitude)
        self.heading = heading_deg

    def set_route(self, geojson: dict[str, object]) -> None:
        self.route = geojson


class MapRendererUiTest(unittest.TestCase):
    def test_heading_is_converted_from_si_without_changing_manual_camera(self) -> None:
        renderer = FakeRenderer()
        ui = MapRendererUi(renderer)
        position = GeoPoint(0.0, 0.0)
        ui.set_map_state(MapState(
            MapViewport(position, 16), follow_enabled=False,
            markers=(MapMarker("vehicle", position, MapMarkerKind.CURRENT_POSITION,
                               heading_rad=math.pi / 2),),
        ))
        self.assertEqual(renderer.heading, 90.0)
        self.assertIsNone(renderer.camera)

    def test_translates_map_snapshot_to_renderer_commands(self) -> None:
        renderer = FakeRenderer()
        ui = MapRendererUi(renderer)
        current = GeoPoint(math.radians(42.8), math.radians(-83.0))
        destination = GeoPoint(math.radians(42.9), math.radians(-82.9))
        ui.set_map_state(
            MapState(
                viewport=MapViewport(
                    current,
                    16.5,
                    bearing_rad=math.radians(25.0),
                    pitch_rad=math.radians(45.0),
                ),
                markers=(
                    MapMarker(
                        "vehicle",
                        current,
                        MapMarkerKind.CURRENT_POSITION,
                    ),
                ),
                route_geometry=RouteGeometry((current, destination)),
            )
        )

        assert renderer.position is not None
        self.assertAlmostEqual(renderer.position[0], 42.8)
        self.assertAlmostEqual(renderer.position[1], -83.0)
        assert renderer.camera is not None
        self.assertAlmostEqual(renderer.camera[0], 42.8)
        self.assertAlmostEqual(renderer.camera[1], -83.0)
        self.assertEqual(renderer.camera[2], 16.5)
        self.assertAlmostEqual(renderer.camera[3], 25.0)
        self.assertAlmostEqual(renderer.camera[4], 45.0)
        assert renderer.route is not None
        geometry = renderer.route["geometry"]
        assert isinstance(geometry, dict)
        coordinates = geometry["coordinates"]
        assert isinstance(coordinates, list)
        self.assertAlmostEqual(coordinates[0][0], -83.0)
        self.assertAlmostEqual(coordinates[0][1], 42.8)

    def test_manual_mode_does_not_override_renderer_camera(self) -> None:
        renderer = FakeRenderer()
        ui = MapRendererUi(renderer)
        center = GeoPoint(math.radians(42.8), math.radians(-83.0))

        ui.set_map_state(
            MapState(
                viewport=MapViewport(center, 16.5),
                follow_enabled=False,
            )
        )

        self.assertIsNone(renderer.camera)

    def test_exposes_connected_request_handler(self) -> None:
        ui = MapRendererUi(FakeRenderer())
        handler = MapRequestHandlerStub()

        ui.set_map_request_handler(handler)

        self.assertIs(ui.request_handler, handler)


if __name__ == "__main__":
    unittest.main()
