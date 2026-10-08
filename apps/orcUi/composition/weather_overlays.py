# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Construct weather providers/controllers outside all frontend widget modules."""

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
    ui = WeatherOverlayUiGroup(view, MapWeatherOverlayUi(renderer, unit_system))
    city = CityWeatherOverlayController(dispatcher, CityWeatherProvider(), MapWeatherCitySource(),
                                        renderer.search_weather_cities, ui)
    model = ModelWeatherOverlayController(dispatcher, tiles, HrrrMapLayerProvider(), ui)
    route = RouteWeatherOverlayController(dispatcher, route_handler, presentation, RouteWeatherProvider(), ui)
    controller = WeatherOverlayController(dispatcher, city, model, route)
    view.set_weather_overlay_request_handler(controller)
    controller.request_replay()
    return controller
