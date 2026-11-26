# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Model overlay readiness and layer-change lifecycle."""

from time import monotonic
from unittest.mock import Mock, patch

from common.units.unit_system import UnitSystem
from controllers.weather.model_weather_overlay_controller import ModelWeatherOverlayController
from controllers.weather.radar_provider_if import RadarFrame
from frontends.common.map_weather_overlay_ui import MapWeatherOverlayUi
from frontends.common.weather_overlay_format import model_legend
from frontends.common.weather_overlay_ui_group import WeatherOverlayUiGroup
from ui.weather.weather_overlay_ui_stub import WeatherOverlayUiStub


def component() -> tuple[ModelWeatherOverlayController, Mock, Mock, WeatherOverlayUiStub]:
    tiles = Mock()
    tiles.tile_url.return_value = "http://127.0.0.1:1234/{z}/{x}/{y}.png"
    native, sink = Mock(), WeatherOverlayUiStub()
    group = WeatherOverlayUiGroup(MapWeatherOverlayUi(native, lambda: UnitSystem.IMPERIAL), sink)
    ui = ModelWeatherOverlayController(Mock(), tiles, Mock(), group)
    return ui, tiles, native, sink


def test_ready_layer_publishes_independently_and_reports_forecast_time() -> None:
    ui, tiles, native, sink = component()
    ui.kind = "temperature"
    tiles.frame_error.return_value = None
    tiles.frame_ready.return_value = True
    frame = RadarFrame(1790946000, "orc-hrrr-layer://fixture", max_zoom=9)
    ui._complete(0, frame, None)
    assert native.set_weather_field.call_count >= 1
    assert "Weather forecast" in ui.status
    assert "Loading" not in ui.status
    assert model_legend(sink.model_state, True)[0][0] == "-22°F"


def test_late_previous_layer_does_not_replace_selected_layer() -> None:
    ui, _, native, _ = component()
    ui.kind = "wind"
    ui._generation = 2
    with patch.object(ui, "refresh") as refresh:
        ui._complete(1, RadarFrame(100, "old"), None)
    assert ui._frame is None
    refresh.assert_called_once()
    native.set_weather_field.assert_not_called()


def test_off_clears_layer_without_touching_radar_or_camera() -> None:
    ui, _, native, _ = component()
    ui.select("off")
    native.set_weather_field.assert_called_with(None, enabled=False)
    native.set_weather_radar.assert_not_called()
    native.set_camera.assert_not_called()


def test_tile_failure_hides_overlay_and_reports_unavailable() -> None:
    ui, tiles, native, _ = component()
    ui.kind = "wind"
    ui._frame = RadarFrame(100, "url")
    tiles.frame_error.return_value = "bad GRIB"
    ui._wait(0, monotonic())
    assert ui._frame is None
    assert "unavailable: bad GRIB" in ui.status
    native.set_weather_field.assert_called_with(None, enabled=False)


def test_forecast_failure_without_message_hides_overlay() -> None:
    ui, _, native, _ = component()
    ui.kind = "temperature"
    ui._frame = RadarFrame(100, "url")

    ui._complete(0, None, "")

    assert ui._frame is None
    assert "Model overlay unavailable" in ui.status
    native.set_weather_field.assert_called_with(None, enabled=False)
