# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from apps.orcUi.navigation_panel import NavigationPanel


class EarthPreloadLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.panel = object.__new__(NavigationPanel)
        self.launcher = Mock()
        self.launcher.is_running.return_value = True
        self.panel._earth_launcher = self.launcher
        self.panel._display = lambda: ":1"
        self.panel._earth_initialized = False
        self.panel._camera_runtime = SimpleNamespace(latest_position=None)
        self.panel._shortcut_status = Mock()

    def test_first_activation_does_not_stop_warm_browser(self) -> None:
        self.panel._prepare_first_earth_launch()
        self.launcher.stop.assert_not_called()
        self.launcher.set_location.assert_not_called()
        self.assertTrue(self.panel._earth_initialized)

    def test_first_activation_sets_location_when_not_running(self) -> None:
        self.launcher.is_running.return_value = False
        self.panel._camera_runtime.latest_position = SimpleNamespace(
            latitude_rad=0.5, longitude_rad=-1.0
        )
        self.panel._prepare_first_earth_launch()
        self.launcher.set_location.assert_called_once()
        self.launcher.stop.assert_not_called()

    def test_destroy_hides_shared_browser_without_stopping(self) -> None:
        self.panel._earth_owned = False
        self.panel._stop_earth_hud = Mock()
        self.panel._earth_map_overlay = Mock()
        self.panel._earth_vehicle = Mock()
        self.panel._detach_earth = Mock()
        with patch("tkinter.Frame.destroy"):
            self.panel.destroy()
        self.launcher.hide.assert_called_once_with(":1")
        self.launcher.stop.assert_not_called()

    def test_destroy_stops_locally_owned_browser(self) -> None:
        self.panel._earth_owned = True
        self.panel._stop_earth_hud = Mock()
        self.panel._earth_map_overlay = Mock()
        self.panel._earth_vehicle = Mock()
        self.panel._detach_earth = Mock()
        with patch("tkinter.Frame.destroy"):
            self.panel.destroy()
        self.launcher.stop.assert_called_once_with(":1")
        self.launcher.hide.assert_not_called()

    def test_embed_reuses_running_browser(self) -> None:
        self.panel._set_earth_layout = Mock()
        self.panel.update_idletasks = Mock()
        self.panel._earth_geometry = Mock(return_value=((0, 0), (800, 400)))
        self.panel._earth_embedder = Mock()
        self.panel._map_host = Mock()
        self.panel._map_host.winfo_id.return_value = 123
        self.panel._earth_chase = Mock()
        self.panel._earth_geolocation = Mock()
        self.panel._earth_vehicle = Mock()
        self.panel._earth_button = Mock()
        self.panel._earth_map_overlay = Mock()
        self.panel._ui = SimpleNamespace(accent_success="green", background="black")
        self.panel._update_follow_button = Mock()
        self.panel._update_chase_button = Mock()
        self.panel._start_earth_hud = Mock()
        self.panel.after = Mock()
        self.panel._embed_earth()
        self.launcher.show.assert_called_once_with(":1")
        self.launcher.launch.assert_not_called()
        self.launcher.stop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
