import unittest

from controllers.map_renderer.map_position_adapter import MapPositionAdapter
from controllers.navigation.navigation_state import PositionState
from protocols.map_renderer.map_renderer_client import (
    MapRendererUnavailableError,
)


class RecordingMapRenderer:
    def __init__(self) -> None:
        self.positions: list[tuple[float, float]] = []
        self.cameras: list[tuple[float, float, float, float, float]] = []

    def set_position(self, latitude: float, longitude: float) -> None:
        self.positions.append((latitude, longitude))

    def set_camera(
        self,
        latitude: float,
        longitude: float,
        zoom: float,
        bearing: float = 0.0,
        pitch: float = 0.0,
    ) -> None:
        self.cameras.append((latitude, longitude, zoom, bearing, pitch))


class MapPositionAdapterTest(unittest.TestCase):
    def test_ignores_report_without_fix(self) -> None:
        renderer = RecordingMapRenderer()
        adapter = MapPositionAdapter(renderer)  # type: ignore[arg-type]

        adapter.update(PositionState(fix_mode=1))

        self.assertEqual([], renderer.positions)
        self.assertEqual([], renderer.cameras)

    def test_updates_marker_and_follow_camera(self) -> None:
        renderer = RecordingMapRenderer()
        adapter = MapPositionAdapter(renderer)  # type: ignore[arg-type]

        adapter.update(
            PositionState(
                latitude_deg=42.1,
                longitude_deg=-83.2,
                speed_mps=12.0,
                course_deg=725.0,
                fix_mode=3,
                source="gpsd",
            )
        )

        self.assertEqual([(42.1, -83.2)], renderer.positions)
        self.assertEqual(
            [(42.1, -83.2, 16.5, 5.0, 45.0)],
            renderer.cameras,
        )

    def test_throttles_camera_but_not_vehicle_marker(self) -> None:
        renderer = RecordingMapRenderer()
        now = [10.0]
        adapter = MapPositionAdapter(
            renderer,  # type: ignore[arg-type]
            minimum_camera_interval_s=1.0,
            clock=lambda: now[0],
        )
        state = PositionState(
            latitude_deg=42.1,
            longitude_deg=-83.2,
            fix_mode=2,
        )

        adapter.update(state)
        now[0] = 10.5
        adapter.update(state)

        self.assertEqual(2, len(renderer.positions))
        self.assertEqual(1, len(renderer.cameras))

    def test_keeps_bearing_when_below_course_speed(self) -> None:
        renderer = RecordingMapRenderer()
        now = [0.0]
        adapter = MapPositionAdapter(
            renderer,  # type: ignore[arg-type]
            minimum_camera_interval_s=0.0,
            clock=lambda: now[0],
        )
        adapter.update(
            PositionState(
                latitude_deg=42.1,
                longitude_deg=-83.2,
                speed_mps=5.0,
                course_deg=90.0,
                fix_mode=3,
            )
        )
        adapter.update(
            PositionState(
                latitude_deg=42.2,
                longitude_deg=-83.3,
                speed_mps=0.1,
                course_deg=180.0,
                fix_mode=3,
            )
        )

        self.assertEqual(90.0, renderer.cameras[-1][3])

    def test_renderer_failure_does_not_escape_callback(self) -> None:
        class UnavailableRenderer(RecordingMapRenderer):
            def set_position(self, latitude: float, longitude: float) -> None:
                raise MapRendererUnavailableError("renderer stopped")

        adapter = MapPositionAdapter(
            UnavailableRenderer(),  # type: ignore[arg-type]
        )

        with self.assertLogs(
            "controllers.map_renderer.map_position_adapter",
            level="WARNING",
        ):
            adapter.update(
                PositionState(
                    latitude_deg=42.1,
                    longitude_deg=-83.2,
                    fix_mode=2,
                )
            )


if __name__ == "__main__":
    unittest.main()
