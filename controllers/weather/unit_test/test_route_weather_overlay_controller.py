# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Forecast results must follow the active route and selected layers."""

from datetime import datetime, timezone
from unittest.mock import Mock

from common.units.unit_system import UnitSystem
from controllers.route_planning.route_planning_types import GeoPoint, RouteResult
from controllers.weather.route_weather import RouteCheckpoint, RouteWeather
from controllers.weather.route_weather_overlay_controller import RouteWeatherOverlayController
from frontends.common.map_weather_overlay_ui import MapWeatherOverlayUi
from frontends.common.weather_overlay_ui_group import WeatherOverlayUiGroup
from ui.weather.weather_overlay_ui_stub import WeatherOverlayUiStub


def component():
    handler = Mock(active_route=None)
    native, sink = Mock(), WeatherOverlayUiStub()
    group = WeatherOverlayUiGroup(MapWeatherOverlayUi(native, lambda: UnitSystem.IMPERIAL), sink)
    ui = RouteWeatherOverlayController(Mock(), handler, Mock(), Mock(), group)
    ui.native, ui.sink = native, sink
    return ui


def forecasts():
    checkpoint = RouteCheckpoint(GeoPoint(42, -83), datetime.now(timezone.utc), 0)
    return (RouteWeather(checkpoint, 0, 75, 16.09344, "snow"),)


def test_markers_include_selected_layers_and_correct_imperial_units():
    ui = component()
    ui._enabled = True
    ui._forecasts = forecasts()
    ui.publish()
    feature = ui.native.set_route_weather.call_args.args[0]["features"][0]
    assert feature["geometry"]["coordinates"] == [-83, 42]
    assert "32°F" in feature["properties"]["label"]
    assert "Precip 75%" in feature["properties"]["label"]
    assert "10 mph" in feature["properties"]["label"]
    ui._layers = {"rain"}
    ui.publish()
    label = ui.native.set_route_weather.call_args.args[0]["features"][0]["properties"]["label"]
    assert "°F" not in label and "mph" not in label


def test_canceled_route_clears_markers_and_rejects_late_results():
    ui = component()
    ui._enabled = True
    ui._forecasts = forecasts()
    ui._route_changed(None)
    assert ui.native.set_route_weather.call_args.args[0]["features"] == []
    ui._complete(0, forecasts(), None)
    assert ui._forecasts == ()


def test_changed_route_retries_instead_of_accepting_previous_route_weather():
    ui = component()
    ui._enabled = True
    ui._route = RouteResult(1, 300, (GeoPoint(42, -83),), ())
    ui._generation = 2
    ui.refresh = Mock()
    ui._complete(1, forecasts(), None)
    assert ui._forecasts == ()
    ui.refresh.assert_called_once()


def test_failed_refresh_clears_old_weather_and_reports_unavailable():
    ui = component()
    ui._enabled = True
    ui._forecasts = forecasts()
    ui._complete(0, (), "offline")
    assert ui._forecasts == ()
    assert "unavailable: offline" in ui._status
    assert ui.native.set_route_weather.call_args.args[0]["features"] == []



def test_guidance_progress_updates_remaining_route_and_completion_clears_it():
    ui = component()
    message = Mock()
    message.data.route_complete = False
    message.data.distance_along_route_m = 100
    message.data.distance_remaining_m = 300
    ui._guidance_changed(message)
    assert ui._progress == 0.25
    ui._forecasts = forecasts()
    message.data.route_complete = True
    ui._guidance_changed(message)
    assert ui._route is None and ui._forecasts == ()


def test_closed_component_ignores_late_completions_and_closes_provider():
    ui = component()
    ui._provider = Mock()
    ui._enabled = True
    ui.close()
    ui._complete(ui._generation, forecasts(), None)
    assert ui._forecasts == ()
    ui._provider.close.assert_called_once()


def test_route_contract_normalizes_temperature_wind_and_probability():
    ui = component()
    ui._enabled = True
    ui._forecasts = forecasts()
    ui.publish()
    point = ui.sink.route_state.points[0]
    assert point.temperature_k == 273.15
    assert point.wind_speed_m_s == 16.09344 / 3.6
    assert point.rain_probability == 0.75
