# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Construct weather providers/controllers outside all frontend widget modules."""

from common.resource_cleanup import ResourceCleanup

from controllers.weather.city_weather import CityWeatherProvider
from controllers.weather.city_weather_overlay_controller import CityWeatherOverlayController
from controllers.weather.hrrr_map_layers import HrrrMapLayerProvider
from controllers.weather.model_weather_overlay_controller import ModelWeatherOverlayController
from controllers.weather.route_weather import RouteWeatherProvider
from controllers.weather.route_weather_overlay_controller import RouteWeatherOverlayController
from controllers.weather.weather_overlay_controller import WeatherOverlayController
from frontends.common.map_weather_overlay_ui import MapWeatherOverlayUi
from frontends.common.weather_overlay_ui_group import WeatherOverlayUiGroup
from protocols.map_renderer.map_weather_city_source import MapWeatherCitySource


def configure_weather_overlays(dispatcher, view, renderer, tiles, unit_system, route_handler, presentation):
    """Wire one semantic request handler to the Tk view and native-map UI adapter."""
    with ResourceCleanup() as cleanup:
        ui = WeatherOverlayUiGroup(view, MapWeatherOverlayUi(renderer, unit_system))
        with ResourceCleanup() as acquired:
            provider = CityWeatherProvider()
            acquired.callback(provider.close)
            source = MapWeatherCitySource()
            acquired.callback(source.close)
            city = CityWeatherOverlayController(dispatcher, provider, source,
                                                renderer.search_weather_cities, ui)
            cleanup.callback(city.close)
            acquired.release()
        with ResourceCleanup() as acquired:
            provider = HrrrMapLayerProvider()
            acquired.callback(provider.close)
            model = ModelWeatherOverlayController(dispatcher, tiles, provider, ui)
            cleanup.callback(model.close)
            acquired.release()
        with ResourceCleanup() as acquired:
            provider = RouteWeatherProvider()
            acquired.callback(provider.close)
            route = RouteWeatherOverlayController(dispatcher, route_handler, presentation, provider, ui)
            cleanup.callback(route.close)
            acquired.release()
        controller = WeatherOverlayController(dispatcher, city, model, route)
        view.set_weather_overlay_request_handler(controller)
        controller.request_replay()
        cleanup.release()
        return controller
