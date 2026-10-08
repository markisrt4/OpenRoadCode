"""Earth overlay geometry, semantic requests, and hide/theme cleanup."""

import tkinter as tk
import unittest
from unittest.mock import Mock

from apps.orcUi.frontend.tk.navigation_panel import NavigationPanel
from ui.navigation.navigation_places_request_handler_if import NavigationPlacesRequestHandlerIf


class EarthOverlayGeometryTest(unittest.TestCase):
    def test_icon_is_inside_map_and_survives_theme_rebuild_without_extra_row(self):
        try:
            root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(str(error))
        self.addCleanup(root.destroy)
        root.geometry("580x340")
        places = Mock(spec=NavigationPlacesRequestHandlerIf)
        places.poll_search_result.return_value = None
        places.poll_selected.return_value = None
        places.poll_action_result.return_value = None
        places.poll_camera_interaction.return_value = False
        places.poll_camera_state.return_value = None
        handler = Mock()
        handler.zoom_level = 16.5
        handler.pitch_rad = 0.0
        panel = NavigationPanel(root, map_request_handler=handler, places_handler=places)
        panel.pack(fill=tk.BOTH, expand=True)
        root.update()
        button = panel._earth_button
        overlay = panel._earth_overlay
        self.assertIs(button.master, overlay)
        self.assertEqual(button.winfo_manager(), "pack")
        self.assertTrue(overlay.winfo_viewable())
        self.assertGreaterEqual(overlay.winfo_rootx(), panel._map_host.winfo_rootx())
        self.assertLessEqual(overlay.winfo_rootx()+overlay.winfo_width(),
                             panel._map_host.winfo_rootx()+panel._map_host.winfo_width())
        self.assertGreaterEqual(button.winfo_width(), 40)
        button.invoke()
        self.assertIn("Select a place", panel._shortcut_status.get())
        places.request_action.assert_not_called()
        panel._online_mode = Mock(online=False)
        panel._refresh_poi_action_buttons()
        self.assertEqual(str(button.cget("state")), "disabled")
        self.assertEqual(root.tk.splitlist(panel._earth_icon["foreground"])[-1],
                         panel._theme_bundle.ui.text_muted)
        button.invoke()
        places.request_action.assert_not_called()
        panel.pack_forget()
        root.update()
        self.assertFalse(overlay.winfo_viewable())
        panel.pack(fill=tk.BOTH, expand=True)
        root.update()
        self.assertTrue(overlay.winfo_viewable())
        panel.set_theme_bundle(panel._theme_bundle)
        root.update()
        self.assertFalse(button.winfo_exists())
        self.assertFalse(overlay.winfo_exists())
        self.assertTrue(panel._earth_button.winfo_exists())
        panel.destroy()
        places.close.assert_called_once()
