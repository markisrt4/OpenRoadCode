# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for ORC navigation panel camera and POI controls."""

import math
import unittest
import os
import tkinter as tk
import pytest
from unittest.mock import Mock, patch

from apps.orcUi.frontend.tk.navigation_panel import NavigationPanel
from controllers.navigation.map_favorites import MapFavorite
from ui.navigation.poi_models import (PoiAction, PoiActionKind, PoiCategory, PointOfInterest, TransitMode)
from ui.navigation import GeoPoint
from ui.navigation import MapControlsDrawerState
from ui.navigation.route_types import TravelMode


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='native host layout needs X11')
def test_first_views_click_allocates_drawer_and_controls_return_below_views():
    from apps.orcUi.theme_runtime import theme_bundle
    from controllers.navigation.map_controls_drawer_controller import MapControlsDrawerController
    from ui.navigation import MapRequestHandlerStub
    from ui.navigation.navigation_places_request_handler_if import NavigationPlacesRequestHandlerIf
    from ui.navigation.navigation_experience_if import NavigationExperienceState
    from ui.theme import ThemeMode

    root = tk.Tk()
    root.geometry('1200x600')
    places = Mock(spec=NavigationPlacesRequestHandlerIf)
    places.poll_search_result.return_value = None
    places.poll_selected.return_value = None
    places.poll_camera_interaction.return_value = False
    drawer = MapControlsDrawerController()
    panel = NavigationPanel(root, map_request_handler=MapRequestHandlerStub(), places_handler=places,
        drawer_handler=drawer, experience_handler=Mock(state=NavigationExperienceState()),
        theme_bundle=theme_bundle(ThemeMode.DARK))
    panel.pack(fill=tk.BOTH, expand=True)
    drawer.set_ui(panel)
    try:
        root.update()
        controls = panel._experience_controls
        full_width = panel._map_host.winfo_width()
        controls.views_button.invoke()
        root.update()
        assert controls._drawer.winfo_ismapped()
        assert controls._drawer.winfo_width() >= 230
        assert controls._drawer.winfo_height() > 100
        assert panel._map_host.winfo_width() < full_width
        assert not panel._map_controls_handle.winfo_ismapped()
        controls.views_button.invoke()
        root.update()
        assert panel._map_host.winfo_width() == full_width
        handle = panel._map_controls_handle
        assert handle.winfo_ismapped()
        assert 0 <= handle.winfo_rooty() - panel._map_host.winfo_rooty() <= 6
        assert abs(handle.winfo_rootx() + handle.winfo_width() -
                   controls.views_button.winfo_rootx() - controls.views_button.winfo_width()) < 10
    finally:
        panel.destroy()
        root.destroy()


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='popup layout requires X11')
@pytest.mark.parametrize('name,source', [('Home', 'saved-destination'), ('Work', 'saved-destination'), ('Panera', 'osm')])
def test_destination_popup_has_visible_themed_waze_action(name, source):
    from apps.orcUi.frontend.tk.navigation_panel_layout import show_poi_card
    from apps.orcUi.theme_runtime import theme_bundle
    from ui.theme import ThemeMode
    root = tk.Tk()
    panel = tk.Frame(root, width=800, height=600)
    panel.pack()
    panel._theme_bundle = theme_bundle(ThemeMode.DARK)
    panel._poi_card = None
    panel._waze_handler = Mock()
    panel._navigate_to_poi_with_waze = Mock()
    panel._navigate_to_poi = Mock()
    panel._execute_poi_action = Mock()
    panel._refresh_poi_action_buttons = Mock()
    panel.online_actions_allowed = True
    poi = PointOfInterest(name, name, PoiCategory.OTHER, GeoPoint(.7, -1.4), source_class=source)
    try:
        show_poi_card(panel, poi)
        root.update()
        button = panel._poi_action_buttons[0]
        assert button.cget('text') == 'Waze'
        assert button.cget('image')
        assert button.winfo_ismapped()
        assert button.winfo_rooty() + button.winfo_height() <= panel._poi_card.winfo_rooty() + panel._poi_card.winfo_height()
        assert button.cget('background') == panel._theme_bundle.ui.control_background
        button.invoke()
        panel._navigate_to_poi_with_waze.assert_called_once_with(poi)
    finally:
        root.destroy()


class NavigationPanelControlTest(unittest.TestCase):
    """Verify semantic requests without requiring an X display."""

    def test_waze_handoff_closes_popup_without_changing_orc_route(self):
        panel = self._panel()
        panel._waze_handler = Mock()
        panel._route_active = True
        panel._poi_card = Mock()
        poi = PointOfInterest('home', 'Home', PoiCategory.OTHER, GeoPoint(.7, -1.4))
        panel._navigate_to_poi_with_waze(poi)
        panel._waze_handler.request_navigate_waze.assert_called_once_with(poi.position)
        panel._poi_card.destroy.assert_called_once_with()
        panel._route_request_handler.request_start_route.assert_not_called()
        self.assertTrue(panel._route_active)

    def test_offline_waze_destination_request_is_ignored(self):
        panel = self._panel()
        panel._waze_handler = Mock()
        panel._online_mode = Mock(online=False)
        panel._navigate_to_poi_with_waze(PointOfInterest('work', 'Work', PoiCategory.OTHER, GeoPoint(0, 0)))
        panel._waze_handler.request_navigate_waze.assert_not_called()

    def _panel(self) -> NavigationPanel:
        panel = object.__new__(NavigationPanel)
        panel._map_platform = None
        panel._waze_handler = None
        panel._experience_handler = None
        panel._request_handler = Mock()
        panel._zoom_level = 16.5
        panel._zoom_text = Mock()
        panel._dimension_text = Mock()
        panel._pitch_rad = 0.0
        panel._follow_enabled = True
        panel._places_handler = Mock()
        panel._online_mode = None
        panel._poi_action_request = None
        panel._poi_launching = False
        panel._poi_action_buttons = []
        panel._earth_button = None
        panel._unsubscribe_online_mode = Mock()
        panel._places_handler.poll_action_result.return_value = None
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
        panel._map_platform = None
        panel._waze_handler = None
        panel._experience_handler = None
        label = Mock()
        label.return_value.winfo_reqheight.return_value = 18
        with patch.multiple(
            "apps.orcUi.frontend.tk.navigation_panel_layout.tk",
            Frame=Mock(), Button=Mock(), Label=label, Menubutton=Mock(), Menu=Mock(), PhotoImage=Mock(), Toplevel=Mock(),
        ):
            build_navigation_panel(panel)
        panel._build_radar_controls.assert_called_once()
        self.assertIsNotNone(panel._simulate_button)
        self.assertIsNotNone(panel._cancel_route_button)

    def test_zoom_preserves_follow_and_requests_zoom(self) -> None:
        panel = self._panel()
        panel._change_zoom(1.0)
        panel._zoom_text.set.assert_called_once_with("17.5")
        panel.set_follow_enabled.assert_not_called()
        self.assertTrue(panel._follow_enabled)
        panel._request_handler.request_zoom.assert_called_once_with(17.5)

    def test_toolbar_zoom_continues_from_native_double_click_camera(self) -> None:
        from ui.navigation.navigation_places_request_handler_if import NavigationCameraState
        panel = self._panel()
        panel._places_handler.poll_camera_state.return_value = NavigationCameraState(
            GeoPoint(math.radians(42.81), math.radians(-83.02)), 18.5, math.radians(25), math.radians(40))
        panel._change_zoom(1)
        panel._request_handler.request_zoom.assert_called_once_with(19.5)
        self.assertAlmostEqual(panel._pitch_rad, math.radians(40))
        panel._places_handler.poll_camera_state.assert_called_once()

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

    def test_dimension_toggle_returns_to_flat_view_without_recenter_or_zoom(self) -> None:
        panel = self._panel()
        panel._toggle_map_dimension()
        self.assertAlmostEqual(panel._pitch_rad, math.radians(60))
        panel._dimension_text.set.assert_called_with("2D")
        panel._request_handler.reset_mock()
        panel._toggle_map_dimension()
        self.assertEqual(panel._pitch_rad, 0.0)
        panel._dimension_text.set.assert_called_with("3D")
        panel._request_handler.request_pitch.assert_called_once_with(0.0)
        panel._request_handler.request_zoom.assert_not_called()
        panel._request_handler.request_recenter.assert_not_called()

    def test_tilt_controls_update_dimension_toggle_label(self) -> None:
        panel = self._panel()
        panel._change_pitch(5)
        panel._dimension_text.set.assert_called_with("2D")
        panel._change_pitch(-5)
        panel._dimension_text.set.assert_called_with("3D")

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

    def test_collapsed_map_controls_release_rail_and_float_handle(self) -> None:
        panel = self._panel()
        panel._map_host = Mock()
        panel._map_controls = Mock()
        panel._map_controls_rail = Mock()
        panel._map_controls_handle = Mock()
        panel.after_idle = Mock()
        panel._refresh_renderer_state = Mock()

        panel.set_map_controls_drawer_state(MapControlsDrawerState(expanded=False))

        panel._map_controls.place_forget.assert_called_once_with()
        panel._map_host.grid_configure.assert_not_called()
        panel._map_controls_rail.pack_forget.assert_called_once_with()
        panel._map_controls_handle.place.assert_called_once_with(
            in_=panel._map_host, relx=1.0, rely=0.0, y=4, anchor="ne", width=140, height=44,
        )
        panel._map_controls_handle.lift.assert_called_once_with()

    def test_expanded_map_controls_replace_floating_handle(self) -> None:
        panel = self._panel()
        panel._map_host = Mock()
        panel._map_controls = Mock()
        panel._map_controls_rail = Mock()
        panel._map_controls_handle = Mock()
        panel.after_idle = Mock()
        panel._refresh_renderer_state = Mock()

        panel.set_map_controls_drawer_state(MapControlsDrawerState(expanded=True))

        panel._map_controls.place.assert_called_once_with(
            in_=panel._map_host, relx=1.0, rely=0.0, anchor="ne", width=140, relheight=1.0,
        )
        panel._map_controls.lift.assert_called_once_with()
        panel._map_host.grid_configure.assert_not_called()
        panel._map_controls_handle.place_forget.assert_called_once_with()

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

    def test_home_shortcut_opens_popup_before_routing(self) -> None:
        panel = self._panel()
        position = GeoPoint(math.radians(42.8), math.radians(-83.0))
        panel._places_handler.favorite.return_value = MapFavorite("home", "Home", position, "123 Main St")
        panel._show_poi_card = Mock()

        panel._destination_shortcut("home")

        panel._route_request_handler.request_start_route.assert_not_called()
        poi = panel._show_poi_card.call_args.args[0]
        self.assertEqual(poi.position, position)
        self.assertEqual(poi.name, "Home")
        self.assertEqual(poi.address, "123 Main St")
        panel._navigate_to_poi(poi)
        panel._route_request_handler.request_start_route.assert_called_once_with(position, TravelMode.AUTO)

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
            TravelMode.AUTO,
        )
        panel._shortcut_status.set.assert_called_with("Routing to Panera Bread")

    def test_poi_order_action_delegates_to_platform_executor(self) -> None:
        panel = self._panel()
        from ui.navigation.navigation_places_request_handler_if import PlaceActionResult
        from apps.orcUi.frontend.tk.navigation_poi_actions import poll_poi_launch_results
        panel._places_handler.request_action.return_value = 1
        panel._places_handler.poll_action_result.return_value = PlaceActionResult(1, 'Opening order in app', True)
        poi = PointOfInterest(
            poi_id="panera",
            name="Panera Bread",
            category=PoiCategory.FOOD,
            position=GeoPoint(math.radians(42.5), math.radians(-83.0)),
        )
        action = PoiAction(PoiActionKind.ORDER, "ORDER", provider_id="panera")

        panel._execute_poi_action(poi, action)
        poll_poi_launch_results(panel)

        panel._places_handler.request_action.assert_called_once_with(poi, action)
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


def test_embedded_platform_keeps_host_geometry_and_enables_follow():
    from ui.navigation.map_platform_if import MapPlatform, MapPlatformState
    panel = object.__new__(NavigationPanel)
    panel._platform_toggle = None
    panel._terrain_active = False
    panel._follow_enabled = True
    panel._native_camera_controls = Mock()
    panel._map_retry_button = Mock()
    panel._follow_button = Mock()
    panel._loading_cover = Mock()
    panel.set_follow_enabled = Mock()
    panel._zoom_text = Mock()
    panel._dimension_text = Mock()
    panel._zoom_level = 16.5
    panel._pitch_rad = .7
    panel.apply_map_platform_state(MapPlatformState(active=MapPlatform.CESIUM, requested=MapPlatform.CESIUM))
    panel._native_camera_controls.grid_remove.assert_not_called()
    panel._follow_button.configure.assert_called_with(state='normal')
    panel.apply_map_platform_state(MapPlatformState())
    panel._follow_button.configure.assert_called_with(state='normal')


def test_terrain_toolbar_routes_camera_actions_without_native_requests():
    from ui.navigation.map_platform_if import MapPlatform, MapPlatformState, ExplorationCameraAction
    panel = object.__new__(NavigationPanel)
    panel._map_platform = Mock(state=MapPlatformState(active=MapPlatform.CESIUM, requested=MapPlatform.CESIUM))
    panel._request_handler = Mock()
    panel._pan(1,0)
    panel._change_zoom(1)
    panel._change_pitch(-5)
    panel._north_up()
    panel._recenter()
    panel._toggle_map_dimension()
    assert [call.args[0] for call in panel._map_platform.request_camera.call_args_list] == [
        ExplorationCameraAction.PAN_UP, ExplorationCameraAction.ZOOM_IN,
        ExplorationCameraAction.PITCH_DOWN, ExplorationCameraAction.NORTH,
        ExplorationCameraAction.RECENTER, ExplorationCameraAction.DIMENSION]
    assert not panel._request_handler.mock_calls


def test_loading_cover_stays_above_map_until_ready():
    from ui.navigation.map_platform_if import MapPlatform, MapPlatformState
    panel = object.__new__(NavigationPanel)
    panel._platform_toggle = None
    panel._terrain_active = False
    panel._follow_enabled = True
    panel._follow_button = Mock()
    panel._loading_cover = Mock()
    panel._map_retry_button = Mock()
    panel._zoom_text = Mock()
    panel._dimension_text = Mock()
    panel.set_follow_enabled = Mock()
    panel.apply_map_platform_state(MapPlatformState(requested=MapPlatform.CESIUM,busy=True))
    panel._loading_cover.grid.assert_called_once()
    panel._loading_cover.lift.assert_called_once()
    panel._loading_cover.grid_remove.assert_not_called()
    panel.apply_map_platform_state(MapPlatformState(active=MapPlatform.CESIUM,requested=MapPlatform.CESIUM,follow_enabled=True))
    panel._loading_cover.grid_remove.assert_called_once()
    panel.set_follow_enabled.assert_called_with(True)


def test_failed_map_has_visible_error_cover_and_retry_control():
    from ui.navigation.map_platform_if import MapPlatformState
    panel = object.__new__(NavigationPanel)
    panel._platform_toggle = None
    panel._terrain_active = False
    panel._follow_enabled = True
    panel._follow_button = Mock()
    panel._loading_cover = Mock()
    panel._map_retry_button = Mock()
    panel._map_host = Mock()
    panel._map_host.winfo_width.return_value = 640
    panel._zoom_text = Mock()
    panel._dimension_text = Mock()
    panel._zoom_level = 16.5
    panel._pitch_rad = 0
    panel.apply_map_platform_state(MapPlatformState(error='A required library is incompatible'))
    assert 'Map unavailable' in panel._loading_cover.configure.call_args.kwargs['text']
    panel._loading_cover.grid.assert_called_once_with()
    panel._map_retry_button.place.assert_called_once()
    panel._loading_cover.grid_remove.assert_not_called()
    panel.apply_map_platform_state(MapPlatformState())
    panel._loading_cover.grid_remove.assert_called_once()


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='real map error overlay needs X11')
def test_map_failure_overlay_and_retry_are_visible_and_actionable_in_tk():
    from ui.navigation.map_platform_if import MapPlatformState
    root = tk.Tk()
    root.geometry('800x500')
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    retry = Mock()
    panel = object.__new__(NavigationPanel)
    panel._platform_toggle = None
    panel._terrain_active = False
    panel._follow_enabled = True
    panel._follow_button = Mock()
    panel._map_host = tk.Frame(root)
    panel._map_host.grid(row=0, column=0, sticky='nsew')
    panel._loading_cover = tk.Label(root)
    panel._map_retry_button = tk.Button(root, text='RETRY MAP', command=retry)
    panel._zoom_text, panel._dimension_text = Mock(), Mock()
    panel._zoom_level, panel._pitch_rad = 16.5, 0
    try:
        root.update()
        panel.apply_map_platform_state(MapPlatformState(error='A required map library is incompatible.'))
        root.update()
        assert panel._loading_cover.winfo_ismapped()
        assert panel._map_retry_button.winfo_ismapped()
        assert 'Map unavailable' in panel._loading_cover.cget('text')
        panel._map_retry_button.invoke()
        retry.assert_called_once_with()
        panel.apply_map_platform_state(MapPlatformState())
        root.update()
        assert not panel._loading_cover.winfo_ismapped()
        assert not panel._map_retry_button.winfo_ismapped()
    finally:
        root.destroy()
