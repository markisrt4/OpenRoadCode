import time
import unittest

from controllers.map_renderer.map_position_adapter import MapPositionAdapter
from controllers.navigation.navigation_state import GroundMotionState, PositionState
from protocols.map_renderer.map_renderer_client import MapRendererUnavailableError


class RecordingMapRenderer:
    def __init__(self) -> None:
        self.positions: list[tuple[float, float]] = []
        self.cameras: list[tuple[float, float, float, float, float]] = []

    def set_position(self, latitude: float, longitude: float) -> None:
        self.positions.append((latitude, longitude))

    def set_camera(self, latitude: float, longitude: float, zoom: float, bearing: float = 0.0, pitch: float = 0.0) -> None:
        self.cameras.append((latitude, longitude, zoom, bearing, pitch))


class MapPositionAdapterTest(unittest.TestCase):
    def test_starts_and_stops_render_loop(self) -> None:
        adapter = MapPositionAdapter(RecordingMapRenderer(), frame_rate_hz=100.0)  # type: ignore[arg-type]
        adapter.start()
        self.assertTrue(adapter.is_running)
        time.sleep(0.02)
        adapter.stop()
        self.assertFalse(adapter.is_running)

    def test_ignores_report_without_fix(self) -> None:
        renderer = RecordingMapRenderer()
        adapter = MapPositionAdapter(renderer)  # type: ignore[arg-type]
        adapter.update(PositionState(fix_mode=1))
        self.assertEqual([], renderer.positions)
        self.assertEqual([], renderer.cameras)

    def test_updates_marker_and_follow_camera(self) -> None:
        renderer = RecordingMapRenderer()
        adapter = MapPositionAdapter(renderer)  # type: ignore[arg-type]
        adapter.update_ground_motion(GroundMotionState(speed_mps=12.0, course_deg=725.0, source="gpsd"))
        adapter.update(PositionState(latitude_deg=42.1, longitude_deg=-83.2, fix_mode=3, source="gpsd"))
        self.assertEqual([(42.1, -83.2)], renderer.positions)
        self.assertEqual([(42.1, -83.2, 16.5, 5.0, 45.0)], renderer.cameras)

    def test_interpolates_marker_between_gps_fixes(self) -> None:
        renderer = RecordingMapRenderer()
        now = [0.0]
        adapter = MapPositionAdapter(renderer, correction_time_s=0.5, snap_distance_m=1000.0, clock=lambda: now[0])  # type: ignore[arg-type]
        adapter.update(PositionState(latitude_deg=42.0, longitude_deg=-83.0, fix_mode=2))
        now[0] = 1.0
        adapter.update(PositionState(latitude_deg=42.001, longitude_deg=-83.0, fix_mode=2))
        now[0] = 1.1
        adapter.render_once()
        displayed_latitude = renderer.positions[-1][0]
        self.assertGreater(displayed_latitude, 42.0)
        self.assertLess(displayed_latitude, 42.001)

    def test_predicts_using_speed_and_course_then_stops(self) -> None:
        renderer = RecordingMapRenderer()
        now = [0.0]
        adapter = MapPositionAdapter(renderer, correction_time_s=0.01, maximum_prediction_age_s=1.5, clock=lambda: now[0])  # type: ignore[arg-type]
        adapter.update_ground_motion(GroundMotionState(speed_mps=10.0, course_deg=0.0))
        adapter.update(PositionState(latitude_deg=42.0, longitude_deg=-83.0, fix_mode=3))
        now[0] = 1.0
        adapter.render_once()
        first_prediction = renderer.positions[-1][0]
        now[0] = 3.0
        adapter.render_once()
        final_prediction = renderer.positions[-1][0]
        now[0] = 4.0
        adapter.render_once()
        self.assertGreater(first_prediction, 42.0)
        self.assertGreater(final_prediction, first_prediction)
        self.assertAlmostEqual(final_prediction, renderer.positions[-1][0])

    def test_snaps_when_fix_is_far_away(self) -> None:
        renderer = RecordingMapRenderer()
        now = [0.0]
        adapter = MapPositionAdapter(renderer, snap_distance_m=75.0, clock=lambda: now[0])  # type: ignore[arg-type]
        adapter.update(PositionState(latitude_deg=42.0, longitude_deg=-83.0, fix_mode=2))
        now[0] = 1.0
        adapter.update(PositionState(latitude_deg=42.01, longitude_deg=-83.0, fix_mode=2))
        adapter.render_once()
        self.assertEqual((42.01, -83.0), renderer.positions[-1])

    def test_keeps_bearing_when_below_course_speed(self) -> None:
        renderer = RecordingMapRenderer()
        now = [0.0]
        adapter = MapPositionAdapter(renderer, minimum_camera_interval_s=0.0, clock=lambda: now[0])  # type: ignore[arg-type]
        adapter.update_ground_motion(GroundMotionState(speed_mps=5.0, course_deg=90.0))
        adapter.update(PositionState(latitude_deg=42.1, longitude_deg=-83.2, fix_mode=3))
        now[0] = 1.0
        adapter.render_once()
        adapter.update_ground_motion(GroundMotionState(speed_mps=0.1, course_deg=180.0))
        adapter.update(PositionState(latitude_deg=42.2, longitude_deg=-83.3, fix_mode=3))
        now[0] = 2.0
        adapter.render_once()
        self.assertEqual(90.0, renderer.cameras[-1][3])

    def test_renderer_failure_does_not_escape_callback(self) -> None:
        class UnavailableRenderer(RecordingMapRenderer):
            def set_position(self, latitude: float, longitude: float) -> None:
                raise MapRendererUnavailableError("renderer stopped")

        adapter = MapPositionAdapter(UnavailableRenderer())  # type: ignore[arg-type]
        with self.assertLogs("controllers.map_renderer.map_position_adapter", level="WARNING"):
            adapter.update(PositionState(latitude_deg=42.1, longitude_deg=-83.2, fix_mode=2))


if __name__ == "__main__":
    unittest.main()
