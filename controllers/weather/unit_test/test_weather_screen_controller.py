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
    callback = dispatcher.dispatch_ui.call_args.args[0]
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
    dispatcher.dispatch_ui.call_args.args[0]()
    view.set_loading.assert_called_with(False)
    view.set_weather_status.assert_called_with('Weather unavailable: offline')
    view.set_weather_state.assert_not_called()


def test_cached_fallback_is_labelled_stale_and_keeps_weather_visible():
    from controllers.weather.weather_state import WeatherState, WeatherSource, CurrentWeather
    dispatcher, backend, view = Mock(), Mock(), Mock()
    state = WeatherState(latitude=42.8, longitude=-83.0, location_name='Home', location_source='test',
                         source=WeatherSource('test', 'Test'), fetched_at=100,
                         current=CurrentWeather(temperature_k=283.15))
    backend.latest.return_value = state
    backend.refresh_if_stale.return_value = state
    controller = WeatherScreenController(dispatcher, backend, view)
    controller._clock = lambda: 1300
    with patch('controllers.weather.weather_screen_controller.threading.Thread'):
        controller.set_visible(True)
    controller._refresh(controller._generation)
    dispatcher.dispatch_ui.call_args.args[0]()
    assert view.set_weather_state.call_args.args[0].current.temperature_k == 283.15
    view.set_weather_status.assert_called_with('Weather: showing saved data (20 min old); refresh unavailable')


def test_data_becomes_stale_while_open_without_hidden_timer_updates():
    from controllers.weather.weather_state import WeatherState, WeatherSource, CurrentWeather
    dispatcher, backend, view = Mock(), Mock(), Mock()
    state = WeatherState(latitude=42.8, longitude=-83.0, location_name='Home', location_source='test',
                         source=WeatherSource('test', 'Test'), fetched_at=100,
                         current=CurrentWeather(temperature_k=283.15))
    controller = WeatherScreenController(dispatcher, backend, view)
    controller._visible = True
    controller._clock = lambda: 110
    controller._complete(0, state, '')
    view.set_weather_status.assert_called_with('')
    monitor = dispatcher.schedule_ui_callback.call_args.args[1]
    controller._clock = lambda: 700
    monitor()
    view.set_weather_status.assert_called_with('Weather: data is 10 min old; refresh to update')
    late = dispatcher.schedule_ui_callback.call_args.args[1]
    controller.set_visible(False)
    view.reset_mock()
    dispatcher.reset_mock()
    late()
    assert view.mock_calls == [] and dispatcher.mock_calls == []
