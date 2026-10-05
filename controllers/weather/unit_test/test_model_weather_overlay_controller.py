# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Model overlay readiness and layer-change lifecycle."""

from unittest.mock import Mock
from time import monotonic

from common.units.unit_system import UnitSystem
from controllers.weather.radar_provider_if import RadarFrame
from controllers.weather.model_weather_overlay_controller import ModelWeatherOverlayController
from frontends.common.map_weather_overlay_ui import MapWeatherOverlayUi
from frontends.common.weather_overlay_ui_group import WeatherOverlayUiGroup
from ui.weather.weather_overlay_ui_stub import WeatherOverlayUiStub
from frontends.common.weather_overlay_format import model_legend


def component():
    tiles = Mock()
    tiles.tile_url.return_value = 'http://127.0.0.1:1234/{z}/{x}/{y}.png'
    native, sink = Mock(), WeatherOverlayUiStub()
    group = WeatherOverlayUiGroup(MapWeatherOverlayUi(native, lambda: UnitSystem.IMPERIAL), sink)
    ui = ModelWeatherOverlayController(Mock(), tiles, Mock(), group)
    ui.native, ui.sink = native, sink
    return ui


def test_ready_layer_publishes_independently_and_reports_forecast_time():
    ui = component()
    ui.kind = 'temperature'
    ui._tiles.frame_error.return_value = None
    ui._tiles.frame_ready.return_value = True
    frame = RadarFrame(1790946000, 'orc-hrrr-layer://fixture', max_zoom=9)
    ui._complete(0, frame, None)
    assert ui.native.set_weather_field.call_count >= 1
    assert 'Weather forecast' in ui.status
    assert 'Loading' not in ui.status
    assert model_legend(ui.sink.model_state, True)[0][0] == '-22°F'


def test_late_previous_layer_does_not_replace_selected_layer():
    ui = component()
    ui.kind = 'wind'
    ui._generation = 2
    ui.refresh = Mock()
    ui._complete(1, RadarFrame(100, 'old'), None)
    assert ui._frame is None
    ui.refresh.assert_called_once()
    ui.native.set_weather_field.assert_not_called()


def test_off_clears_layer_without_touching_radar_or_camera():
    ui = component()
    ui.select('off')
    ui.native.set_weather_field.assert_called_with(None, enabled=False)
    ui.native.set_weather_radar.assert_not_called()
    ui.native.set_camera.assert_not_called()


def test_tile_failure_hides_overlay_and_reports_unavailable():
    ui = component()
    ui.kind = 'wind'
    ui._frame = RadarFrame(100, 'url')
    ui._tiles.frame_error.return_value = 'bad GRIB'
    ui._wait(0, monotonic())
    assert ui._frame is None
    assert 'unavailable: bad GRIB' in ui.status
    ui.native.set_weather_field.assert_called_with(None, enabled=False)
