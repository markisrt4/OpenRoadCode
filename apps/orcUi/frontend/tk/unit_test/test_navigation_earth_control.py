"""POI-scoped Earth requests, offline presentation, and popup lifecycle."""

import tkinter as tk
import unittest
from unittest.mock import Mock

from apps.orcUi.frontend.tk.navigation_panel import NavigationPanel
from controllers.navigation.map_controls_drawer_controller import MapControlsDrawerController
from apps.orcUi.frontend.tk.navigation_poi_actions import poll_poi_launch_results
from ui.navigation import GeoPoint
from ui.navigation.navigation_places_request_handler_if import NavigationPlacesRequestHandlerIf, PlaceActionResult
from ui.navigation.poi_models import PoiAction, PoiActionKind, PoiCategory, PointOfInterest


class EarthPoiControlTest(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(str(error))
        self.addCleanup(self.root.destroy)
        self.root.geometry("580x340")
        self.places = Mock(spec=NavigationPlacesRequestHandlerIf)
        self.places.poll_search_result.return_value = None
        self.places.poll_selected.return_value = None
        self.places.poll_action_result.return_value = None
        self.places.poll_camera_interaction.return_value = False
        self.places.poll_camera_state.return_value = None
        self.places.request_action.return_value = 7
        handler = Mock(zoom_level=16.5, pitch_rad=0.0)
        self.panel = NavigationPanel(
            self.root,
            map_request_handler=handler,
            places_handler=self.places,
            drawer_handler=MapControlsDrawerController(),
        )
        self.panel.pack(fill=tk.BOTH, expand=True)
        self.root.update()
        self.action = PoiAction(PoiActionKind.OPEN_WEBSITE, "Explore in Google Earth",
                                provider_id="google-earth-explore",
                                uri="https://earth.google.com/web/search/42,-83")
        self.poi = PointOfInterest("poi", "Selected place", PoiCategory.OTHER,
                                   GeoPoint(.7, -1.4), actions=(self.action,))

    def show(self, poi=None):
        self.panel._show_poi_card(poi or self.poi)
        self.root.update()
        return self.panel._earth_button

    def test_globe_only_appears_in_poi_popup_and_launches_its_exact_destination(self):
        self.assertIsNone(self.panel._earth_button)
        self.assertFalse(any(isinstance(w, tk.Toplevel) for w in self.panel.winfo_children()))
        button = self.show()
        self.assertIs(button.winfo_toplevel(), self.panel._poi_card)
        self.assertTrue(self.panel._earth_icon.transparency_get(0, 0))
        self.assertFalse(self.panel._earth_icon.transparency_get(23, 23))
        self.assertGreaterEqual(button.winfo_rootx(), self.panel._poi_card.winfo_rootx())
        self.assertLessEqual(button.winfo_rootx()+button.winfo_width(),
                             self.panel._poi_card.winfo_rootx()+self.panel._poi_card.winfo_width())
        button.invoke()
        self.places.request_action.assert_called_once_with(self.poi, self.action)
        self.assertEqual(str(button.cget("state")), "disabled")
        self.places.poll_action_result.return_value = PlaceActionResult(7, "Opened Earth", True)
        poll_poi_launch_results(self.panel)
        self.assertFalse(button.winfo_exists())

    def test_action_row_has_icons_above_labels_and_close_returns_to_map(self):
        earth = self.show()
        buttons = [child for child in earth.master.winfo_children() if isinstance(child, tk.Button)]
        self.assertEqual([button.cget("text") for button in buttons], ["Navigate", "Earth", "Close"])
        self.assertEqual(len({button.winfo_y() for button in buttons}), 1)
        for button in buttons:
            self.assertEqual(str(button.cget("compound")), "top")
            self.assertTrue(button.cget("image"))
            self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),
                                 self.panel._poi_card.winfo_rooty()+self.panel._poi_card.winfo_height())
        buttons[-1].invoke()
        self.assertFalse(earth.winfo_exists())
        self.assertTrue(self.panel._map_host.winfo_viewable())
        self.places.request_action.assert_not_called()

    def test_offline_greys_and_disables_icon_and_online_restores_it(self):
        self.panel._online_mode = Mock(online=False)
        button = self.show()
        self.assertEqual(str(button.cget("state")), "disabled")
        self.assertEqual(str(button.cget("image")), str(self.panel._earth_offline_icon))
        button.invoke()
        self.places.request_action.assert_not_called()
        self.panel._online_mode.online = True
        self.panel._refresh_poi_action_buttons()
        self.assertEqual(str(button.cget("state")), "normal")
        self.assertEqual(str(button.cget("image")), str(self.panel._earth_icon))
        button.invoke()
        self.places.request_action.assert_called_once_with(self.poi, self.action)

    def test_replacing_popup_does_not_retarget_click_or_close_new_card_on_old_completion(self):
        old_button = self.show()
        old_button.invoke()
        new_action = PoiAction(PoiActionKind.OPEN_WEBSITE, "Explore in Google Earth",
                               provider_id="google-earth-explore",
                               uri="https://earth.google.com/web/search/43,-84")
        new_poi = PointOfInterest("other", "Other place", PoiCategory.OTHER,
                                  GeoPoint(.75, -1.45), actions=(new_action,))
        new_button = self.show(new_poi)
        self.assertFalse(old_button.winfo_exists())
        self.assertEqual(str(new_button.cget("state")), "disabled")
        self.places.poll_action_result.return_value = PlaceActionResult(7, "Opened Earth", True)
        poll_poi_launch_results(self.panel)
        self.assertTrue(new_button.winfo_exists())
        new_button.invoke()
        self.places.request_action.assert_called_with(new_poi, new_action)

    def test_hide_theme_and_close_leave_no_popup_or_globe(self):
        button = self.show()
        self.panel.set_theme_bundle(self.panel._theme_bundle)
        self.root.update()
        self.assertFalse(button.winfo_exists())
        self.assertIsNone(self.panel._earth_button)
        button = self.show()
        self.panel.close_places()
        self.assertFalse(button.winfo_exists())
        self.panel.destroy()
        self.places.close.assert_called_once()

    def test_place_without_earth_action_has_no_globe(self):
        poi = PointOfInterest("unavailable", "Unavailable", PoiCategory.OTHER, GeoPoint(0, 0))
        self.assertIsNone(self.show(poi))
