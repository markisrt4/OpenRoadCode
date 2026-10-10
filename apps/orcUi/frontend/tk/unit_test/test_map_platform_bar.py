"""Exercise real map-selector geometry and semantic requests."""

import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import Mock

from apps.orcUi.frontend.tk.map_platform_bar import MapPlatformBar
from apps.orcUi.frontend.tk.navigation_screen import NavigationScreen
from ui.navigation.map_platform_if import MapPlatform, MapPlatformState
from ui.theme import load_theme_bundle


class MapPlatformBarTest(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"Tk display unavailable: {error}")
        self.addCleanup(self.root.destroy)
        self.root.geometry("480x340")
        self.handler = Mock()
        project = Path(__file__).resolve().parents[5]
        theme = load_theme_bundle(project / "resources/themes/orc-dark.css")
        self.bar = MapPlatformBar(self.root, handler=self.handler, theme=theme)
        self.bar.pack(fill=tk.X)

    def test_selector_emits_requests_and_keeps_long_status_visible(self):
        self.bar._buttons[MapPlatform.EARTH].invoke()
        self.handler.request_platform.assert_called_once_with(MapPlatform.EARTH)
        self.bar.set_state(MapPlatformState(MapPlatform.EARTH, MapPlatform.EARTH, False,
            "Earth — ORC GPS; route/POI overlays remain on MapLibre"))
        self.root.update()
        self.bar._chase.invoke()
        self.handler.request_chase.assert_called_once()
        self.assertLess(self.bar.winfo_height(), 170)
        self.assertGreaterEqual(self.bar._status.winfo_height(), self.bar._status.winfo_reqheight())

    def test_pending_startup_disables_duplicate_platform_and_chase_actions(self):
        self.bar.set_state(MapPlatformState(requested=MapPlatform.EARTH, busy=True))
        self.bar._buttons[MapPlatform.EARTH].invoke()
        self.bar._chase.invoke()
        self.handler.request_platform.assert_not_called()
        self.handler.request_chase.assert_not_called()


class MapPlatformPollTest(unittest.TestCase):
    def test_stale_poll_does_not_touch_destroyed_or_replaced_widgets(self):
        screen = object.__new__(NavigationScreen)
        screen._platform_generation = 2
        screen._panel = Mock()
        screen._map_platform = Mock()
        screen._platform_bar = Mock()
        screen._host = Mock()
        screen._poll_platform(1)
        screen._map_platform.resize.assert_not_called()
        screen._platform_bar.set_state.assert_not_called()
        screen._host.schedule_ui_callback.assert_not_called()
