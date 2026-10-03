# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Forecast refresh lifecycle regression tests."""
from unittest.mock import Mock, patch
from controllers.weather.weather_screen_controller import WeatherScreenController
from ui.weather.weather_screen_ui_if import WeatherScreenUiIf
from frontends.tk.weather.weather_screen import WeatherScreen


def test_weather_screen_implements_contract():
    assert issubclass(WeatherScreen, WeatherScreenUiIf)
    assert not WeatherScreen.__abstractmethods__


def test_hidden_screen_discards_failure_and_close_disconnects():
    dispatcher, backend, view = Mock(), Mock(), Mock()
    backend.latest.return_value = None
    backend.refresh_if_stale.side_effect = RuntimeError('offline')
    controller = WeatherScreenController(dispatcher, backend, view)
    with patch('controllers.weather.weather_screen_controller.threading.Thread'):
        controller.set_visible(True)
    controller._refresh(controller._generation)
    callback = dispatcher.schedule_ui_callback.call_args.args[1]
    controller.set_visible(False)
    view.reset_mock()
    callback()
    view.set_weather_status.assert_not_called()
    controller.close()
    view.set_weather_request_handler.assert_called_once_with(None)


def test_visible_failure_stops_loading_and_preserves_forecast():
    dispatcher, backend, view = Mock(), Mock(), Mock()
    backend.latest.return_value = None
    backend.refresh_if_stale.side_effect = RuntimeError('offline')
    controller = WeatherScreenController(dispatcher, backend, view)
    with patch('controllers.weather.weather_screen_controller.threading.Thread'):
        controller.set_visible(True)
    controller._refresh(controller._generation)
    dispatcher.schedule_ui_callback.call_args.args[1]()
    view.set_loading.assert_called_with(False)
    view.set_weather_status.assert_called_with('Weather: offline')
    view.set_weather_state.assert_not_called()
