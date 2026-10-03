# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Weather UI boundaries must reject incomplete handlers and preserve immutable SI state."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from ui.navigation.navigation_places_request_handler_if import NavigationPlacesFactoryIf
from unittest.mock import Mock

import pytest

from apps.orcUi.frontend.tk.navigation_route_weather import NavigationRouteWeather
from apps.orcUi.frontend.tk.navigation_screen import NavigationScreen
from controllers.weather.weather_overlay_controller import WeatherOverlayController
from ui.weather.weather_overlay_request_handler_if import WeatherOverlayRequestHandlerIf
from ui.weather.weather_overlay_controls_if import WeatherOverlayControlsIf
from ui.weather.weather_overlay_state import CityWeatherOverlayState
from ui.weather.weather_overlay_ui_if import WeatherOverlayUiIf
from ui.weather.weather_overlay_ui_stub import WeatherOverlayUiStub
from ui.weather.radar_request_handler_if import RadarRequestHandlerIf
from ui.weather.radar_controls_if import RadarControlsIf
from ui.weather.radar_ui_if import RadarUiState


def test_overlay_state_is_immutable_and_naive_mutation_cannot_change_controls():
    state = CityWeatherOverlayState(anchor=datetime.now(timezone.utc))
    with pytest.raises(FrozenInstanceError):
        state.hours = 24
    assert WeatherOverlayUiStub().city_state == CityWeatherOverlayState()


def test_both_weather_control_views_implement_explicit_contracts():
    assert issubclass(NavigationRouteWeather, WeatherOverlayControlsIf)
    assert issubclass(NavigationScreen, RadarControlsIf)
    assert not NavigationRouteWeather.__abstractmethods__
    assert not NavigationScreen.__abstractmethods__
    with pytest.raises(TypeError):
        WeatherOverlayRequestHandlerIf()
    with pytest.raises(TypeError):
        RadarRequestHandlerIf()
    with pytest.raises(TypeError):
        WeatherOverlayUiIf()


def test_weather_view_rejects_an_arbitrary_backend_object_as_a_handler():
    view = NavigationRouteWeather(Mock(), Mock(), Mock())
    with pytest.raises(TypeError):
        view.set_weather_overlay_request_handler(object())
    view.set_weather_overlay_request_handler(None)


def test_weather_controls_emit_semantic_requests_and_only_store_snapshots():
    view = NavigationRouteWeather(Mock(), Mock(), Mock())
    handler = Mock(spec=WeatherOverlayRequestHandlerIf)
    view.set_weather_overlay_request_handler(handler)
    state = CityWeatherOverlayState(hours=12)
    view.set_city_weather_state(state)
    assert view._city_state is state
    view._enabled_var = Mock()
    view._enabled_var.get.return_value = True
    view._set_enabled()
    handler.request_route_enabled.assert_called_once_with(True)
    view._layer_vars = {'temperature': Mock(), 'wind': Mock()}
    view._layer_vars['temperature'].get.return_value = True
    view._layer_vars['wind'].get.return_value = False
    view._set_layers()
    handler.request_route_layers.assert_called_once_with(frozenset({'temperature'}))


def test_radar_view_uses_requests_and_presentation_without_a_controller():
    view = NavigationScreen(Mock(), places_factory=Mock(spec=NavigationPlacesFactoryIf), map_runtime=Mock(), map_request_handler=Mock(),
                            route_request_handler=Mock(), route_simulation_handler=Mock(),
                            theme_bundle=Mock(), telemetry_profile_request=None, on_back=Mock())
    with pytest.raises(TypeError):
        view.set_radar_request_handler(object())
    handler = Mock(spec=RadarRequestHandlerIf)
    view.set_radar_request_handler(handler)
    view.set_radar_enabled(True)
    handler.request_enabled.assert_called_once_with(True)
    view.set_radar_state(RadarUiState(enabled=True, times=(100, 200)))
    assert view.radar_enabled
    view._radar_seek(1)
    handler.request_seek.assert_called_once_with(1)
    assert '_radar_controller' not in view.__dict__


def test_hidden_navigation_cancels_periodic_forecasts_and_replay_requests():
    city, model, route, dispatcher = Mock(), Mock(), Mock(), Mock()
    controller = WeatherOverlayController(dispatcher, city, model, route)
    controller.request_navigation_visible(True)
    timer = dispatcher.schedule_ui_callback.call_args.args[1]
    controller.request_navigation_visible(False)
    model.refresh.reset_mock()
    route.refresh.reset_mock()
    timer()
    controller.request_replay()
    model.refresh.assert_not_called()
    route.refresh.assert_not_called()
    city.hide.assert_called_once()


def test_closed_overlay_composition_releases_each_owned_backend_once():
    city, model, route = Mock(), Mock(), Mock()
    controller = WeatherOverlayController(Mock(), city, model, route)
    controller.close()
    controller.close()
    for child in (city, model, route):
        child.close.assert_called_once()


def test_one_failing_backend_close_cannot_skip_other_owned_resources():
    city, model, route = Mock(), Mock(), Mock()
    city.close.side_effect = RuntimeError('failed close')
    controller = WeatherOverlayController(Mock(), city, model, route)
    with pytest.raises(RuntimeError, match='failed close'):
        controller.close()
    model.close.assert_called_once()
    route.close.assert_called_once()
