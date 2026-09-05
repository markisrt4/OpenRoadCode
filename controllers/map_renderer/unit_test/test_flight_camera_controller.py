# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import unittest

from controllers.map_renderer.flight_camera_controller import FlightCameraController, FlightState


class RecordingMapRenderer:
    def __init__(self) -> None:
        self.positions: list[tuple[float, float]] = []
        self.cameras: list[dict[str, float]] = []

    def set_position(self, latitude: float, longitude: float) -> None:
        self.positions.append((latitude, longitude))

    def set_camera(self, latitude: float, longitude: float, zoom: float, bearing: float = 0.0, pitch: float = 0.0) -> None:
        self.cameras.append({"latitude": latitude, "longitude": longitude, "zoom": zoom, "bearing": bearing, "pitch": pitch})


class FlightCameraControllerTest(unittest.TestCase):
    def test_forward_motion_advances_virtual_position(self) -> None:
        renderer = RecordingMapRenderer()
        controller = FlightCameraController(renderer, FlightState(42.0, -83.0, heading_deg=0.0, speed_mps=100.0))  # type: ignore[arg-type]
        controller.render_once(10.0)
        state = controller.render_once(11.0)
        self.assertGreater(state.latitude_deg, 42.0)
        self.assertAlmostEqual(state.longitude_deg, -83.0, places=4)
        self.assertEqual(renderer.cameras[-1]["bearing"], 0.0)

    def test_controls_are_clamped_and_heading_wraps(self) -> None:
        renderer = RecordingMapRenderer()
        controller = FlightCameraController(renderer, FlightState(42.0, -83.0, heading_deg=358.0, speed_mps=1.0))  # type: ignore[arg-type]
        state = controller.adjust(speed_delta_mps=-10.0, heading_delta_deg=5.0, pitch_delta_deg=100.0, zoom_delta=100.0)
        self.assertEqual(state.speed_mps, 0.0)
        self.assertEqual(state.heading_deg, 3.0)
        self.assertEqual(state.pitch_deg, 60.0)
        self.assertEqual(state.zoom, 19.0)

    def test_render_publishes_position_and_camera(self) -> None:
        renderer = RecordingMapRenderer()
        controller = FlightCameraController(renderer, FlightState(42.5, -83.25, heading_deg=90.0, pitch_deg=50.0, zoom=12.0))  # type: ignore[arg-type]
        controller.render_once(1.0)
        self.assertEqual(renderer.positions[-1], (42.5, -83.25))
        self.assertEqual(renderer.cameras[-1], {"latitude": 42.5, "longitude": -83.25, "zoom": 12.0, "bearing": 90.0, "pitch": 50.0})


if __name__ == "__main__":
    unittest.main()
