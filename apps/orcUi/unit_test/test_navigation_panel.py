# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for ORC navigation panel camera and POI controls."""

import math
import unittest
from unittest.mock import Mock

from apps.orcUi.navigation_panel import NavigationPanel
from controllers.navigation.map_favorites import MapFavorite
from controllers.poi import PoiAction, PoiActionKind, PoiCategory, PointOfInterest, TransitMode
from ui.navigation import GeoPoint
from ui.navigation.route_types import TravelMode


class NavigationPanelControlTest(unittest.TestCase):
    """Verify semantic requests without requiring an X display."""

    def _panel(self) -> NavigationPanel:
        panel = object.__new__(NavigationPanel)
        panel._request_handler = Mock()
        panel._zoom_level = 16.5
        panel._zoom_text = Mock()
        panel._follow_enabled = True
        panel._poi_controller = Mock()
        panel._shortcut_status = Mock()
        panel._active_poi_render_category = ""
        panel._route_request_handler = Mock()
        panel._route_simulation_handler = Mock()
        panel._route_active = False
        panel._simulation_active = False
        panel._simulate_button = Mock()
        panel._map_favorites = Mock()
        panel.after = Mock()
        panel.set_follow_enabled = Mock(side_effect=lambda enabled: setattr(panel, "_follow_enabled", enabled))
        return panel

    def test_manual_zoom_disables_follow_and_requests_zoom(self) -> None:
        panel = self._panel()
        panel._change_zoom(1.0)
        panel._zoom_text.set.assert_called_once_with("17.5")
        panel.set_follow_enabled.assert_called_once_with(False)
        panel._request_handler.request_zoom.assert_called_once_with(17.5)

    def test_north_up_disables_follow(self) -> None:
        panel = self._panel(); panel._north_up()
        panel.set_follow_enabled.assert_called_once_with(False)
        panel._request_handler.request_bearing.assert_called_once_with(0.0)

    def test_recenter_restores_follow(self) -> None:
        panel = self._panel(); panel._follow_enabled = False; panel._recenter()
        panel.set_follow_enabled.assert_called_once_with(True)
        panel._request_handler.request_recenter.assert_called_once_with()

    def test_toggle_follow_emits_semantic_request(self) -> None:
        panel = self._panel(); panel._toggle_follow()
        panel.set_follow_enabled.assert_called_once_with(False)
        panel._request_handler.request_follow.assert_called_once_with(False)

    def test_gas_shortcut_starts_fuel_search(self) -> None:
        panel = self._panel(); panel._start_poi_search = Mock(); panel._destination_shortcut("gas")
        panel._start_poi_search.assert_called_once_with(PoiCategory.FUEL)

    def test_grocery_shortcut_starts_grocery_search(self) -> None:
        panel = self._panel(); panel._start_poi_search = Mock(); panel._destination_shortcut("grocery")
        panel._start_poi_search.assert_called_once_with(PoiCategory.GROCERY)

    def test_food_shortcut_starts_food_search(self) -> None:
        panel = self._panel(); panel._start_poi_search = Mock(); panel._destination_shortcut("food")
        panel._start_poi_search.assert_called_once_with(PoiCategory.FOOD)

    def test_home_shortcut_starts_route_to_saved_home(self) -> None:
        panel = self._panel()
        position = GeoPoint(math.radians(42.8), math.radians(-83.0))
        panel._map_favorites.home = MapFavorite("home", "Home", position)

        panel._destination_shortcut("home")

        panel._route_request_handler.request_start_route.assert_called_once_with(
            position,
            (),
            TravelMode.AUTO,
        )
        panel._shortcut_status.set.assert_called_with("Routing to Home")

    def test_work_shortcut_reports_unconfigured_location(self) -> None:
        panel = self._panel()
        panel._map_favorites.work = None

        panel._destination_shortcut("work")

        panel._route_request_handler.request_start_route.assert_not_called()
        panel._shortcut_status.set.assert_called_with("Work location not configured")

    def test_sim_drive_starts_active_route_simulation(self) -> None:
        panel = self._panel()
        panel._route_active = True

        panel._toggle_route_simulation()

        panel._route_simulation_handler.request_start_route_simulation.assert_called_once_with(
            time_scale=60.0
        )
        self.assertTrue(panel._simulation_active)
        panel._shortcut_status.set.assert_called_with("Simulating route at 60×")

    def test_sim_drive_toggle_stops_active_simulation(self) -> None:
        panel = self._panel()
        panel._route_active = True
        panel._simulation_active = True

        panel._toggle_route_simulation()

        panel._route_simulation_handler.request_stop_route_simulation.assert_called_once_with()
        self.assertFalse(panel._simulation_active)
        panel._shortcut_status.set.assert_called_with("Route simulation stopped")

    def test_issue_poi_search_forwards_default_mode(self) -> None:
        panel = self._panel(); panel._poi_controller = Mock(); panel._shortcut_status = Mock(); panel._poi_search_after_id = "pending"
        panel._issue_poi_search(PoiCategory.FUEL)
        self.assertIsNone(panel._poi_search_after_id)
        panel._poi_controller.search.assert_called_once_with(PoiCategory.FUEL, TransitMode.ALL)
        panel._shortcut_status.set.assert_called_once_with("Searching nearby fuel…")

    def test_issue_poi_search_forwards_transit_mode(self) -> None:
        panel = self._panel(); panel._poi_controller = Mock(); panel._shortcut_status = Mock(); panel._poi_search_after_id = "pending"
        panel._issue_poi_search(PoiCategory.TRANSIT, TransitMode.BUS)
        panel._poi_controller.search.assert_called_once_with(PoiCategory.TRANSIT, TransitMode.BUS)
        panel._shortcut_status.set.assert_called_once_with("Searching nearby bus…")


if __name__ == "__main__":
    unittest.main()


    def test_poi_navigate_action_starts_route_to_selected_poi(self) -> None:
        panel = self._panel()
        poi = PointOfInterest(
            poi_id="panera",
            name="Panera Bread",
            category=PoiCategory.FOOD,
            position=GeoPoint(math.radians(42.5), math.radians(-83.0)),
        )
        panel._poi_card = None

        panel._execute_poi_action(
            poi,
            PoiAction(PoiActionKind.NAVIGATE, "NAVIGATE"),
        )

        panel._route_request_handler.request_start_route.assert_called_once_with(
            poi.position,
            (),
            TravelMode.AUTO,
        )
        panel._shortcut_status.set.assert_called_with("Routing to Panera Bread")

    def test_poi_app_order_action_uses_app_or_uri_launcher(self) -> None:
        panel = self._panel()
        panel._android_launcher = Mock()
        panel._android_launcher.open_package_or_uri.return_value = "app"
        panel._poi_card = None
        poi = PointOfInterest(
            poi_id="panera",
            name="Panera Bread",
            category=PoiCategory.FOOD,
            position=GeoPoint(math.radians(42.5), math.radians(-83.0)),
        )

        panel._execute_poi_action(
            poi,
            PoiAction(
                PoiActionKind.OPEN_APP_OR_URI,
                "ORDER",
                uri="https://www.panerabread.com/en-us/start-an-order.html",
                android_package="com.panera.bread",
            ),
        )

        panel._android_launcher.open_package_or_uri.assert_called_once_with(
            "com.panera.bread",
            "https://www.panerabread.com/en-us/start-an-order.html",
        )
        panel._shortcut_status.set.assert_called_with("Opening order in app")
