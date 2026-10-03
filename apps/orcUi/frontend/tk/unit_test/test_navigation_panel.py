# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for ORC navigation panel camera and POI controls."""

import math
import unittest
from unittest.mock import Mock, patch

from apps.orcUi.frontend.tk.navigation_panel import NavigationPanel
from controllers.navigation.map_favorites import MapFavorite
from ui.navigation.poi_models import (PoiAction, PoiActionKind, PoiCategory, PointOfInterest, TransitMode)
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
        panel._places_handler = Mock()
        panel._shortcut_status = Mock()
        panel._active_poi_render_category = ""
        panel._active_poi_search = None
        panel._route_request_handler = Mock()
        panel._route_simulation_handler = Mock()
        panel._route_active = False
        panel._simulation_active = False
        panel._simulate_button = Mock()
        panel._cancel_route_button = Mock()
        panel._poi_card = None
        panel._poi_search_after_id = None
        panel._places_closed = False
        panel._closed = False
        panel._poi_poll_after_id = None
        panel.after = Mock()
        panel.after_cancel = Mock()
        panel.set_follow_enabled = Mock(
            side_effect=lambda enabled: setattr(panel, "_follow_enabled", enabled)
        )
        return panel

    def test_radar_toggle_preserves_camera_and_route_state(self) -> None:
        panel = self._panel()
        panel._radar_enabled = False
        panel._on_radar_toggle = Mock()
        panel._render_radar_state = Mock()
        panel._route_active = True

        panel._toggle_radar()
        self.assertEqual(panel._zoom_level, 16.5)
        panel._request_handler.request_zoom.assert_not_called()
        panel._on_radar_toggle.assert_called_with(True)
        panel._toggle_radar()
        self.assertEqual(panel._zoom_level, 16.5)
        panel._request_handler.request_zoom.assert_not_called()
        panel._on_radar_toggle.assert_called_with(False)
        self.assertTrue(panel._route_active)

    def test_layout_builds_radar_alongside_poi_and_route_controls(self) -> None:
        from apps.orcUi.frontend.tk.navigation_panel_layout import build_navigation_panel

        panel = Mock()
        with patch.multiple(
            "apps.orcUi.frontend.tk.navigation_panel_layout.tk",
            Frame=Mock(), Button=Mock(), Label=Mock(), Menubutton=Mock(), Menu=Mock(),
        ):
            build_navigation_panel(panel)
        panel._build_radar_controls.assert_called_once()
        self.assertIsNotNone(panel._simulate_button)
        self.assertIsNotNone(panel._cancel_route_button)
        self.assertIsNotNone(panel._places_menu)

    def test_zoom_preserves_follow_and_requests_zoom(self) -> None:
        panel = self._panel()
        panel._change_zoom(1.0)
        panel._zoom_text.set.assert_called_once_with("17.5")
        panel.set_follow_enabled.assert_not_called()
        self.assertTrue(panel._follow_enabled)
        panel._request_handler.request_zoom.assert_called_once_with(17.5)

    def test_3d_view_tilts_and_zooms_current_viewport(self) -> None:
        panel = self._panel()
        panel._pitch_rad = 0.0
        panel._schedule_active_poi_refresh = Mock()

        panel._show_3d_view()

        self.assertEqual(panel._zoom_level, 17.0)
        self.assertAlmostEqual(panel._pitch_rad, math.radians(60.0))
        panel._zoom_text.set.assert_called_once_with("17.0")
        panel.set_follow_enabled.assert_called_once_with(False)
        panel._request_handler.request_zoom.assert_called_once_with(17.0)
        panel._request_handler.request_pitch.assert_called_once_with(math.radians(60.0))
        panel._request_handler.request_recenter.assert_not_called()
        panel._schedule_active_poi_refresh.assert_called_once_with()

    def test_north_up_disables_follow(self) -> None:
        panel = self._panel()
        panel._north_up()
        panel.set_follow_enabled.assert_called_once_with(False)
        panel._request_handler.request_bearing.assert_called_once_with(0.0)

    def test_recenter_restores_follow(self) -> None:
        panel = self._panel()
        panel._follow_enabled = False
        panel._recenter()
        panel.set_follow_enabled.assert_called_once_with(True)
        panel._request_handler.request_recenter.assert_called_once_with()

    def test_toggle_follow_emits_semantic_request(self) -> None:
        panel = self._panel()
        panel._toggle_follow()
        panel.set_follow_enabled.assert_called_once_with(False)
        panel._request_handler.request_follow.assert_called_once_with(False)

    def test_gas_shortcut_starts_fuel_search(self) -> None:
        panel = self._panel()
        panel._start_poi_search = Mock()
        panel._destination_shortcut("gas")
        panel._start_poi_search.assert_called_once_with(PoiCategory.FUEL)

    def test_grocery_shortcut_starts_grocery_search(self) -> None:
        panel = self._panel()
        panel._start_poi_search = Mock()
        panel._destination_shortcut("grocery")
        panel._start_poi_search.assert_called_once_with(PoiCategory.GROCERY)

    def test_food_shortcut_starts_food_search(self) -> None:
        panel = self._panel()
        panel._start_poi_search = Mock()
        panel._destination_shortcut("food")
        panel._start_poi_search.assert_called_once_with(PoiCategory.FOOD)

    def test_home_shortcut_starts_route_to_saved_home(self) -> None:
        panel = self._panel()
        position = GeoPoint(math.radians(42.8), math.radians(-83.0))
        panel._places_handler.favorite.return_value = MapFavorite("home", "Home", position)

        panel._destination_shortcut("home")

        panel._route_request_handler.request_start_route.assert_called_once_with(
            position,
            (),
            TravelMode.AUTO,
        )
        panel._shortcut_status.set.assert_called_with("Routing to Home")

    def test_work_shortcut_reports_unconfigured_location(self) -> None:
        panel = self._panel()
        panel._places_handler.favorite.return_value = None

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

    def test_cancel_route_stops_simulation_and_clears_active_route(self) -> None:
        panel = self._panel()
        panel._route_active = True
        panel._simulation_active = True
        panel._guidance_instruction = Mock()
        panel._guidance_detail = Mock()

        panel._cancel_route()

        panel._route_simulation_handler.request_stop_route_simulation.assert_called_once_with()
        panel._route_request_handler.request_cancel_route.assert_called_once_with()
        self.assertFalse(panel._route_active)
        self.assertFalse(panel._simulation_active)
        panel._guidance_instruction.set.assert_called_once_with("")
        panel._guidance_detail.set.assert_called_once_with("")
        panel._shortcut_status.set.assert_called_with("Route cancelled")

    def test_clear_poi_search_removes_rendered_results(self) -> None:
        panel = self._panel()
        panel._active_poi_render_category = "transit"

        panel._clear_poi_search()

        panel._places_handler.clear.assert_called_once_with()
        panel._request_handler.request_poi_focus.assert_called_once_with(None)
        panel._request_handler.request_poi_results.assert_called_once_with((), "")
        self.assertEqual("", panel._active_poi_render_category)
        panel._shortcut_status.set.assert_called_once_with("")

    def test_clear_poi_search_cancels_pending_search(self) -> None:
        panel = self._panel()
        panel._poi_search_after_id = "pending-search"

        panel._clear_poi_search()

        panel.after_cancel.assert_called_once_with("pending-search")
        self.assertIsNone(panel._poi_search_after_id)
        panel._places_handler.clear.assert_called_once_with()

    def test_issue_poi_search_forwards_default_mode(self) -> None:
        panel = self._panel()
        panel._places_handler = Mock()
        panel._shortcut_status = Mock()
        panel._poi_search_after_id = "pending"
        panel._issue_poi_search(PoiCategory.FUEL)
        self.assertIsNone(panel._poi_search_after_id)
        panel._places_handler.search.assert_called_once_with(PoiCategory.FUEL, TransitMode.ALL)
        panel._shortcut_status.set.assert_called_once_with("Searching nearby fuel…")

    def test_issue_poi_search_forwards_transit_mode(self) -> None:
        panel = self._panel()
        panel._places_handler = Mock()
        panel._shortcut_status = Mock()
        panel._poi_search_after_id = "pending"
        panel._issue_poi_search(PoiCategory.TRANSIT, TransitMode.BUS)
        panel._places_handler.search.assert_called_once_with(PoiCategory.TRANSIT, TransitMode.BUS)
        panel._shortcut_status.set.assert_called_once_with("Searching nearby bus…")

    def test_poi_navigate_action_starts_route_to_selected_poi(self) -> None:
        panel = self._panel()
        poi = PointOfInterest(
            poi_id="panera",
            name="Panera Bread",
            category=PoiCategory.FOOD,
            position=GeoPoint(math.radians(42.5), math.radians(-83.0)),
        )
        panel._poi_card = None

        panel._navigate_to_poi(poi)

        panel._route_request_handler.request_start_route.assert_called_once_with(
            poi.position,
            (),
            TravelMode.AUTO,
        )
        panel._shortcut_status.set.assert_called_with("Routing to Panera Bread")

    def test_poi_order_action_delegates_to_platform_executor(self) -> None:
        panel = self._panel()
        panel._places_handler.execute.return_value = "Opening order in app"
        poi = PointOfInterest(
            poi_id="panera",
            name="Panera Bread",
            category=PoiCategory.FOOD,
            position=GeoPoint(math.radians(42.5), math.radians(-83.0)),
        )
        action = PoiAction(PoiActionKind.ORDER, "ORDER", provider_id="panera")

        panel._execute_poi_action(poi, action)

        panel._places_handler.execute.assert_called_once_with(poi, action)
        panel._shortcut_status.set.assert_called_with("Opening order in app")


if __name__ == "__main__":
    unittest.main()


def test_close_places_cancels_poll_and_debounce_and_rejects_late_callbacks():
    panel = NavigationPanelControlTest()._panel()
    panel._poi_poll_after_id = 'poll'
    panel._poi_search_after_id = 'debounce'
    panel.close_places()
    panel.close_places()
    assert {call.args[0] for call in panel.after_cancel.call_args_list} == {'poll', 'debounce'}
    panel._places_handler.close.assert_called_once_with()
    panel._places_handler.reset_mock()
    panel._shortcut_status.reset_mock()
    panel._issue_poi_search(PoiCategory.FOOD)
    panel._poll_poi_events()
    assert panel._places_handler.mock_calls == []
    panel._shortcut_status.set.assert_not_called()
