# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import unittest
from unittest.mock import Mock

from apps.orcUi.frontend.tk.navigation_places_controls import NavigationPlacesControls
from ui.navigation.map_ui_if import GeoPoint
from ui.navigation.navigation_places_request_handler_if import MapFavorite
from ui.navigation.route_types import TravelMode


class SavedDestinationControlsTest(unittest.TestCase):
    def panel(self):
        panel = NavigationPlacesControls()
        panel._places_handler = Mock()
        panel._request_handler = Mock()
        panel._route_request_handler = Mock()
        panel._shortcut_status = Mock()
        panel._poi_search_after_id = "pending-search"
        panel.after_cancel = Mock()
        panel.after = Mock()
        panel._poi_card = Mock()
        panel._poi_card.winfo_exists.return_value = True
        panel._show_poi_card = Mock()
        panel._update_simulation_button = Mock()
        return panel

    def test_home_and_work_open_popup_and_wait_for_navigate(self):
        for key in ("home", "work"):
            with self.subTest(key=key):
                panel = self.panel()
                old_card = panel._poi_card
                position = GeoPoint(0.7, -1.4)
                panel._places_handler.favorite.return_value = MapFavorite(
                    key, key.title(), position, "123 Main St",
                )
                panel._destination_shortcut(key)
                panel.after_cancel.assert_called_once_with("pending-search")
                old_card.destroy.assert_called_once()
                self.assertIsNone(panel._poi_search_after_id)
                panel._places_handler.clear.assert_called_once()
                panel._route_request_handler.request_start_route.assert_not_called()
                poi = panel._show_poi_card.call_args.args[0]
                self.assertEqual(poi.address, "123 Main St")
                self.assertEqual(poi.name, key.title())
                panel._navigate_to_poi(poi)
                panel._route_request_handler.request_start_route.assert_called_once_with(
                    position, (), TravelMode.AUTO,
                )

    def test_unconfigured_destination_clears_old_popup_without_routing(self):
        panel = self.panel()
        old_card = panel._poi_card
        panel._places_handler.favorite.return_value = None
        panel._destination_shortcut("work")
        old_card.destroy.assert_called_once()
        panel._show_poi_card.assert_not_called()
        panel._route_request_handler.request_start_route.assert_not_called()
        panel._shortcut_status.set.assert_called_with("Work location not configured")
