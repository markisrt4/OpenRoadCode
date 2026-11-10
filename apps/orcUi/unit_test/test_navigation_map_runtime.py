"""Alternative-map lifecycle, request routing, and stale completion tests."""

import threading
import unittest
from unittest.mock import Mock
from types import SimpleNamespace

from apps.orcUi.navigation_map_runtime import NavigationMapRuntime
from ui.navigation import MapRequestHandlerIf
from ui.navigation.map_platform_if import MapPlatform


class NavigationMapRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.native = Mock()
        self.requests = Mock(spec=MapRequestHandlerIf)
        self.earth = Mock()
        self.earth.WINDOW_CLASS = "earth"
        self.earth.is_running.return_value = False
        self.earth.prepare.side_effect = lambda display: setattr(self.earth.is_running, "return_value", True)
        self.earth.stop.side_effect = lambda display: setattr(self.earth.is_running, "return_value", False)
        self.embedder = Mock()
        self.embedder.window_id = None
        self.embedder.embed.side_effect = lambda *args, **kwargs: setattr(self.embedder, "window_id", 42)
        self.embedder.clear.side_effect = lambda: setattr(self.embedder, "window_id", None)
        self.controller = Mock()
        self.controller.status = "Earth — test GPS"
        self.runtime = NavigationMapRuntime(self.native, self.requests, self.earth,
            controller=self.controller, embedder=self.embedder)
        self.runtime._devtools = Mock()
        self.runtime._devtools.targets.return_value = [SimpleNamespace(url="about:blank")]
        self.runtime._devtools.command.return_value = {}
        self.addCleanup(self.runtime.close)
        self.runtime.resize(800, 400, 999)
        self.runtime.launch(100)

    def flush(self):
        self.runtime._worker.submit(lambda: None).result(timeout=3)

    def select_earth(self):
        self.runtime.request_platform(MapPlatform.EARTH)
        self.flush()

    def test_switches_back_and_recreates_browser_before_loading_earth(self):
        self.select_earth()
        self.assertEqual(MapPlatform.EARTH, self.runtime.state.active)
        self.embedder.embed.assert_called_once_with(0, 100, 800, 400, window_class="earth")
        self.runtime.request_platform(MapPlatform.MAPLIBRE)
        self.flush()
        self.embedder.detach.assert_not_called()
        self.earth.stop.assert_called_once()
        self.select_earth()
        self.assertEqual(self.earth.prepare.call_count, 2)
        self.earth.show.assert_not_called()

    def test_manual_camera_requests_route_to_active_platform(self):
        self.runtime.requests.request_zoom(17.5)
        self.flush()
        self.controller.request_zoom.assert_not_called()
        self.select_earth()
        self.runtime.requests.request_pan_screen(right_px=100, up_px=-50)
        self.runtime.requests.request_zoom(18)
        self.flush()
        self.controller.request_pan_screen.assert_called_once_with(100, -50)
        self.controller.request_zoom.assert_called_once_with(18)
        self.requests.request_pan_screen.assert_called_once_with(100, -50)

    def test_embedding_failure_returns_to_native_map(self):
        self.embedder.embed.side_effect = RuntimeError("no X11 window")
        self.select_earth()
        self.assertEqual(MapPlatform.MAPLIBRE, self.runtime.state.active)
        self.assertIn("no X11 window", self.runtime.state.status)
        self.native.launch.assert_called_with(100)

    def test_switch_during_startup_does_not_embed_stale_browser(self):
        entered, release = threading.Event(), threading.Event()
        def launch(display):
            entered.set()
            release.wait(3)
            self.earth.is_running.return_value = True
        self.earth.prepare.side_effect = launch
        self.runtime.request_platform(MapPlatform.EARTH)
        self.assertTrue(entered.wait(3))
        self.runtime.request_platform(MapPlatform.MAPLIBRE)
        release.set()
        self.flush()
        self.embedder.embed.assert_not_called()
        self.assertEqual(MapPlatform.MAPLIBRE, self.runtime.state.active)

    def test_hide_closes_before_transient_host_can_be_destroyed(self):
        self.select_earth()
        self.runtime.stop()
        self.embedder.detach.assert_not_called()
        self.earth.stop.assert_called_once()
        self.native.stop.assert_called()
        self.runtime.launch(200)
        self.flush()
        self.assertEqual(self.earth.prepare.call_count, 2)
        self.assertEqual(self.embedder.embed.call_args.args[1], 200)

    def test_close_rejects_pending_and_future_work(self):
        self.select_earth()
        self.runtime.close()
        calls = self.earth.mock_calls[:]
        self.runtime.request_platform(MapPlatform.EARTH)
        self.runtime.requests.request_zoom(18)
        self.runtime.launch(300)
        self.assertEqual(calls, self.earth.mock_calls)
        self.controller.close.assert_called_once()

    def test_offline_rejects_earth_without_stopping_native_map(self):
        self.runtime._online_allowed = lambda: False
        self.runtime.request_platform(MapPlatform.EARTH)
        self.flush()
        self.earth.prepare.assert_not_called()
        self.assertEqual(MapPlatform.MAPLIBRE, self.runtime.state.active)

    def test_browser_exit_restores_native_map(self):
        self.select_earth()
        self.earth.is_running.return_value = False
        self.runtime._worker.submit(self.runtime._tick, self.runtime._generation).result(3)
        self.assertEqual(MapPlatform.MAPLIBRE, self.runtime.state.active)
        self.assertIn("exited", self.runtime.state.status)

    def test_gps_ticks_do_not_reconfigure_unchanged_surface(self):
        self.select_earth()
        for _ in range(3):
            self.runtime._worker.submit(self.runtime._tick, self.runtime._generation).result(3)
        self.embedder.resize.assert_not_called()
        self.runtime.resize(640, 360, 999)
        for _ in range(2):
            self.runtime._worker.submit(self.runtime._tick, self.runtime._generation).result(3)
        self.embedder.resize.assert_called_once_with(640, 360)

    def test_reembedding_applies_size_even_if_previous_host_had_same_size(self):
        self.select_earth()
        self.runtime.stop()
        self.runtime.launch(200)
        self.flush()
        self.assertEqual(self.embedder.embed.call_count, 2)
        self.embedder.embed.assert_called_with(0, 200, 800, 400, window_class="earth")

    def test_page_navigation_occurs_only_after_embedding(self):
        calls = Mock()
        calls.attach_mock(self.embedder, "embedder")
        calls.attach_mock(self.runtime._devtools, "devtools")
        self.select_earth()
        names = [call[0] for call in calls.mock_calls]
        self.assertLess(names.index("embedder.embed"), names.index("devtools.command"))
        self.runtime._devtools.command.assert_called_once_with(
            self.runtime._devtools.targets.return_value[0], "Page.navigate",
            {"url": "https://earth.google.com/web"})

    def test_navigation_failure_restores_maplibre_and_closes_browser(self):
        self.runtime._devtools.command.return_value = {"errorText": "network error"}
        # Expire the retry window after one attempt.
        from unittest.mock import patch
        with patch("apps.orcUi.navigation_map_runtime.time.monotonic", side_effect=[0, 0, 9]):
            self.select_earth()
        self.assertEqual(self.runtime.state.active, MapPlatform.MAPLIBRE)
        self.earth.stop.assert_called_once()
        self.native.launch.assert_called_with(100)
