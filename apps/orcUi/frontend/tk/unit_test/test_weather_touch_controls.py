# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Touch weather actions, state synchronization and popup lifetime without X11."""
from dataclasses import replace
from unittest.mock import Mock

from apps.orcUi.frontend.tk.city_weather_controls import CityWeatherControls
from apps.orcUi.frontend.tk.navigation_route_weather import NavigationRouteWeather
from ui.weather.weather_overlay_request_handler_if import WeatherOverlayRequestHandlerIf
from ui.weather.weather_overlay_state import CityWeatherOverlayState


def city_controls():
    view = object.__new__(CityWeatherControls)
    view._handler = Mock(spec=WeatherOverlayRequestHandlerIf)
    view._state = CityWeatherOverlayState(hours=6)
    view._updating = False
    for name in ('_hours', '_enabled', '_scale', '_time', '_status', '_play', '_refresh'):
        setattr(view, name, Mock())
    view._fields = {key: (Mock(), key) for key in ('temperature', 'wind', 'precipitation')}
    view._periods = {key: (Mock(), key) for key in ('past', 'future')}
    return view


def test_city_snapshots_select_buttons_without_emitting_scrub_requests():
    view = city_controls()
    view._hours.set.side_effect = view._scrub
    state = replace(view._state, kind='wind', period='past', hours=12, enabled=True)
    view.set_state(state)
    assert view._state is state
    assert not view._handler.mock_calls
    assert view._fields['wind'][0].configure_button.call_args.kwargs['selected']
    assert not view._fields['temperature'][0].configure_button.call_args.kwargs['selected']
    assert view._periods['past'][0].configure_button.call_args.kwargs['selected']


def test_city_touch_actions_use_snapshots_and_retired_controls_emit_nothing():
    view = city_controls()
    handler = view._handler
    view._select_field('wind')
    handler.request_city_selection.assert_called_with('wind', view._state.period, 6)
    view._select_period('past')
    handler.request_city_selection.assert_called_with(view._state.kind, 'past', 6)
    view._toggle_enabled()
    handler.request_city_enabled.assert_called_once_with(True)
    view._toggle_playback()
    handler.request_city_playback.assert_called_once_with(True)
    view.close()
    handler.reset_mock()
    view._select_field('temperature')
    view._select_period('future')
    view._toggle_enabled()
    view._toggle_playback()
    view._refresh_cities()
    view._scrub('24')
    assert not handler.mock_calls


def test_closing_weather_releases_owned_grab_and_retires_city_requests_once():
    view = NavigationRouteWeather(Mock(), Mock(), Mock())
    handler = Mock(spec=WeatherOverlayRequestHandlerIf)
    view.set_weather_overlay_request_handler(handler)
    popup = view._popup = Mock()
    popup.grab_current.return_value = popup
    city = view._city_controls = city_controls()
    old_handler = city._handler
    view._close_popup()
    view._close_popup()
    popup.grab_release.assert_called_once()
    popup.destroy.assert_called_once()
    old_handler.reset_mock()
    city._toggle_playback()
    assert not old_handler.mock_calls
    assert view._popup is None and view._city_controls is None


def test_weather_outside_taps_and_hidden_buttons_cannot_act_on_new_screen():
    view = NavigationRouteWeather(Mock(), Mock(), Mock())
    popup = view._popup = Mock()
    popup.winfo_rootx.return_value = popup.winfo_rooty.return_value = 100
    popup.winfo_width.return_value = 660
    popup.winfo_height.return_value = 550
    popup.grab_current.return_value = popup
    view._outside_popup_press(Mock(x_root=150, y_root=150))
    popup.destroy.assert_not_called()
    assert view._outside_popup_press(Mock(x_root=50, y_root=50)) == 'break'
    callback, variable = Mock(), Mock()
    view._toggle_value(variable, callback)
    variable.set.assert_not_called()
    callback.assert_not_called()


def test_city_playback_compacts_without_grabbing_map_and_stop_requests_pause():
    view = NavigationRouteWeather(Mock(), Mock(), Mock())
    handler = Mock(spec=WeatherOverlayRequestHandlerIf)
    view.set_weather_overlay_request_handler(handler)
    popup = view._popup = Mock()
    popup.grab_current.return_value = popup
    view._weather_compact = False
    view._popup_body, view._city_playback_bar = Mock(), Mock()
    view._position_weather_popup = Mock()
    view._set_city_compact(True)
    view._popup_body.pack_forget.assert_called_once()
    popup.grab_release.assert_called_once()
    popup.grab_set.assert_not_called()
    view._stop_city_playback()
    handler.request_city_playback.assert_called_once_with(False)
    view._set_city_compact(False)
    view._city_playback_bar.pack_forget.assert_called_once()
    popup.grab_set.assert_called_once()
    view._close_popup()
    handler.reset_mock()
    view._stop_city_playback()
    handler.request_city_playback.assert_not_called()
