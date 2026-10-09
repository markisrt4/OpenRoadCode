# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Weather correlation, quiet refreshes, invalidation, and privacy without sockets."""

from datetime import datetime, timezone
from io import BytesIO
import json
import logging
from time import monotonic
from unittest.mock import Mock, patch

from PIL import Image
import pytest

from common.logging.structured import JsonFormatter, validate_event
from controllers.route_planning.route_planning_types import GeoPoint, RouteResult
from controllers.weather.city_weather import CityWeatherHours, WeatherCity
from controllers.weather.city_weather_overlay_controller import CityWeatherOverlayController
from controllers.weather.model_weather_overlay_controller import ModelWeatherOverlayController
from controllers.weather.radar_palette import RadarPalette
from controllers.weather.radar_provider_if import RadarFrame
from controllers.weather.radar_replay_controller import RadarReplayController
from controllers.weather.radar_tile_service import RadarTileService
from controllers.weather.route_weather import RouteCheckpoint, RouteWeather
from controllers.weather.route_weather_overlay_controller import RouteWeatherOverlayController
from controllers.weather.weather_controller import WeatherController
from controllers.weather.weather_radar_controller import WeatherRadarController
from controllers.weather.weather_screen_controller import WeatherScreenController
from controllers.weather.weather_state import CurrentWeather, WeatherLocation, WeatherSource, WeatherState
from ui.weather.radar_ui_stub import RadarUiStub
from ui.weather.weather_overlay_ui_stub import WeatherOverlayUiStub

PRIVATE = "private-location https://private.test/?token=private /private/cache 42.8028 -83.0127"


def records(caplog, component=None):
    result = [json.loads(JsonFormatter().format(r)) for r in caplog.records
              if r.name.startswith("weather.") and (component is None or r.name == component)]
    allowed = {"timestamp", "level", "component", "event", "message", "pid", "operation_id",
               "stage", "reason", "exception_type", "item_count", "frame_count", "byte_count",
               "frame_index", "enabled", "visible", "playing", "kind", "palette", "forecast"}
    for record in result:
        validate_event(record)
        assert set(record) <= allowed
    text = json.dumps(result)
    for private in ("private", "42.8028", "-83.0127", "latitude", "longitude", "tile_url",
                    "temperature_k", "error_message", "stack_trace"):
        assert private not in text
    return result


def state():
    return WeatherState(42.8028, -83.0127, "private-location", "private-location",
                        WeatherSource("private-provider", "private-provider"), 100, CurrentWeather())


def forecast_controller():
    provider = Mock()
    provider.provider_id = "private-provider"
    provider.refresh.return_value = state()
    controller = WeatherController(provider, fallback_location=WeatherLocation(42.8028, -83.0127, PRIVATE, PRIVATE),
                                   clock=lambda: 1000)
    return controller, provider


def test_forecast_failure_recovery_and_fresh_cache_are_private_and_quiet(caplog):
    caplog.set_level(logging.DEBUG)
    controller, provider = forecast_controller()
    provider.refresh.side_effect = [OSError(PRIVATE), OSError(PRIVATE), state()]
    for _ in range(2):
        with pytest.raises(OSError):
            controller.refresh()
    controller.refresh()
    controller.refresh_if_stale(1000)
    emitted = records(caplog)
    transitions = [r for r in emitted if r["level"] != "DEBUG"]
    assert [r["event"] for r in transitions] == ["weather.failed", "weather.recovered"]
    assert transitions[0]["exception_type"] == "OSError"
    requests = [r for r in emitted if r["event"] == "weather.requested"]
    assert len({r["operation_id"] for r in requests}) == 3
    assert transitions[-1]["operation_id"] == requests[-1]["operation_id"]
    assert provider.refresh.call_count == 3
    assert emitted[-1]["event"] == "weather.cache_used"


def test_failed_refresh_retains_cached_forecast_and_never_logs_its_location(caplog):
    caplog.set_level(logging.DEBUG)
    controller, provider = forecast_controller()
    cached = controller.refresh()
    provider.refresh.side_effect = RuntimeError(PRIVATE)
    assert controller.refresh_if_stale(1) is cached
    emitted = records(caplog)
    assert emitted[-1]["event"] == "weather.cache_used"
    failure = next(r for r in emitted if r["event"] == "weather.failed")
    assert emitted[-1]["operation_id"] == failure["operation_id"]


def test_location_failure_and_recovery_do_not_record_gps_details(caplog):
    caplog.set_level(logging.INFO)
    controller, _ = forecast_controller()
    location = Mock()
    location.get_location.side_effect = [OSError(PRIVATE), OSError(PRIVATE), WeatherLocation(42.8028, -83.0127, PRIVATE, PRIVATE)]
    controller._location_provider = location
    for _ in range(3):
        controller.refresh()
    emitted = records(caplog)
    assert [r["event"] for r in emitted] == ["weather.failed", "weather.recovered"]
    assert {r["stage"] for r in emitted} == {"location"}


def test_offline_cache_stays_quiet_and_missing_cache_reports_once(caplog):
    caplog.set_level(logging.INFO)
    controller, provider = forecast_controller()
    cached = controller.refresh()
    controller._network_allowed = lambda: False
    for _ in range(3):
        assert controller.refresh() is cached
    assert records(caplog) == []
    controller._last_state = None
    for _ in range(2):
        with pytest.raises(RuntimeError):
            controller.refresh()
    assert [r["reason"] for r in records(caplog)] == ["offline_without_cache"]
    provider.refresh.assert_called_once()


def overlay(kind):
    host, provider, ui = Mock(), Mock(), WeatherOverlayUiStub()
    if kind == "city":
        city = WeatherCity("private-location", 42.8028, -83.0127)
        provider.hourly.return_value = (CityWeatherHours(city, (100,), (1,), (2,), (3,)),)
        controller = CityWeatherOverlayController(host, provider, Mock(), Mock(), ui)
        controller.enabled, controller._visible, controller._cities = True, True, (city,)
        call = provider.hourly
    elif kind == "model":
        tiles = Mock()
        tiles.frame_error.return_value = None
        tiles.frame_ready.return_value = True
        tiles.tile_url.return_value = "https://private.test/tiles"
        provider.get_frame.return_value = RadarFrame(100, "https://private.test/?token=private")
        controller = ModelWeatherOverlayController(host, tiles, provider, ui)
        controller.kind = "temperature"
        call = provider.get_frame
    else:
        route = RouteResult(1000, 300, (GeoPoint(42.8028, -83.0127), GeoPoint(43, -83)), ())
        handler = Mock(active_route=route)
        provider.forecast.return_value = (RouteWeather(RouteCheckpoint(route.shape[0], datetime.now(timezone.utc), 0), 1, 2, 3, PRIVATE),)
        controller = RouteWeatherOverlayController(host, handler, Mock(), provider, ui)
        controller._enabled = True
        call = provider.forecast
    module = type(controller).__module__
    return controller, call, host, module


def test_radar_provider_discovery_failure_and_recovery_exclude_urls(caplog):
    caplog.set_level(logging.DEBUG)
    provider = Mock()
    frames = (RadarFrame(100, PRIVATE), RadarFrame(200, PRIVATE))
    provider.get_frames.side_effect = [RuntimeError(PRIVATE), RuntimeError(PRIVATE), frames]
    backend = WeatherRadarController(provider, Mock())
    for _ in range(2):
        with pytest.raises(RuntimeError):
            backend.load_frames()
    assert backend.load_frames() == frames
    emitted = records(caplog)
    assert [r["event"] for r in emitted if r["level"] != "DEBUG"] == ["weather.failed", "weather.recovered"]
    assert emitted[-1]["frame_count"] == 2
    assert emitted[-1]["operation_id"] == emitted[-2]["operation_id"]


def test_unchanged_radar_visibility_and_palette_are_quiet(caplog):
    caplog.set_level(logging.INFO)
    backend = WeatherRadarController(Mock(), Mock())
    backend.hide()
    backend.set_palette(RadarPalette.UNIVERSAL)
    assert records(caplog) == []
    backend.set_palette(RadarPalette.CLASSIC)
    backend.set_palette(RadarPalette.CLASSIC)
    assert [r["event"] for r in records(caplog)] == ["radar.palette_changed"]


def load(controller, host, module):
    with patch(module + ".threading.Thread") as worker:
        controller.refresh()
        worker.call_args.kwargs["target"]()
    return host.schedule_ui_callback.call_args.args[1]


@pytest.mark.parametrize("kind", ["city", "model", "route"])
def test_overlay_worker_correlates_success_to_accepted_ui_result(caplog, kind):
    caplog.set_level(logging.DEBUG)
    controller, _, host, module = overlay(kind)
    callback = load(controller, host, module)
    callback()
    emitted = records(caplog, "weather." + kind)
    assert "overlay.applied" in [r["event"] for r in emitted]
    assert len({r["operation_id"] for r in emitted if "operation_id" in r}) == 1


@pytest.mark.parametrize("kind", ["city", "model", "route"])
def test_overlay_provider_failures_are_transition_only_and_recover(caplog, kind):
    caplog.set_level(logging.INFO)
    controller, call, host, module = overlay(kind)
    success = call.return_value
    call.side_effect = [RuntimeError(PRIVATE), RuntimeError(PRIVATE), success]
    for _ in range(3):
        load(controller, host, module)()
    emitted = records(caplog, "weather." + kind)
    assert [r["event"] for r in emitted] == ["weather.failed", "weather.recovered"]
    assert emitted[0]["exception_type"] == "RuntimeError"


@pytest.mark.parametrize("kind", ["city", "model", "route"])
@pytest.mark.parametrize("invalidate", ["generation", "close"])
def test_late_overlay_result_is_discarded_without_applied_event(caplog, kind, invalidate):
    caplog.set_level(logging.DEBUG)
    controller, _, host, module = overlay(kind)
    callback = load(controller, host, module)
    if invalidate == "close":
        controller.close()
    else:
        controller._generation += 1
        controller.refresh = Mock()
    callback()
    emitted = records(caplog, "weather." + kind)
    assert emitted[-1]["event"] == "weather.result_discarded"
    assert not any(r["event"] == "overlay.applied" for r in emitted)


@pytest.mark.parametrize("kind", ["city", "model", "route"])
def test_worker_start_failure_is_safe_and_correlated(caplog, kind):
    caplog.set_level(logging.DEBUG)
    controller, _, _, module = overlay(kind)
    with patch(module + ".threading.Thread") as worker:
        worker.return_value.start.side_effect = RuntimeError(PRIVATE)
        with pytest.raises(RuntimeError):
            controller.refresh()
    emitted = records(caplog, "weather." + kind)
    assert emitted[-1]["stage"] == "worker"
    assert emitted[-1]["operation_id"] == emitted[0]["operation_id"]


@pytest.mark.parametrize("failure", [False, True])
def test_late_radar_download_or_failure_cannot_reenable_overlay(caplog, failure):
    caplog.set_level(logging.DEBUG)
    provider, renderer = Mock(), Mock()
    provider.get_frames.return_value = (RadarFrame(100, "https://private.test/tiles"),)
    if failure:
        provider.get_frames.side_effect = RuntimeError(PRIVATE)
    backend = WeatherRadarController(provider, renderer)
    host = Mock()
    controller = RadarReplayController(host, RadarUiStub(), backend)
    with patch("controllers.weather.radar_replay_controller.threading.Thread") as worker:
        controller.request_enabled(True)
        target = worker.call_args.kwargs["target"]
        controller.request_enabled(False)
        target()
    host.schedule_ui_callback.call_args.args[1]()
    assert not backend.enabled
    emitted = records(caplog, "weather.radar.replay")
    assert emitted[-1]["event"] == "weather.result_discarded"
    assert not any(r["event"] in {"weather.failed", "weather.recovered"} for r in emitted)
    assert not any(r["event"] == "weather.completed" and r["stage"] != "worker" for r in emitted)


def test_radar_playback_pauses_on_hide_and_old_tick_stays_quiet(caplog):
    caplog.set_level(logging.INFO)
    provider = Mock()
    provider.get_frames.return_value = (RadarFrame(100, PRIVATE), RadarFrame(200, PRIVATE))
    backend = WeatherRadarController(provider, Mock())
    backend.show_latest()
    controller = RadarReplayController(Mock(), RadarUiStub(), backend)
    controller.request_navigation_visible(True)
    controller.request_play_pause()
    tick = controller._host.schedule_ui_callback.call_args.args[1]
    controller.request_navigation_visible(False)
    before = len(caplog.records)
    tick()
    assert len(caplog.records) == before
    emitted = [r for r in records(caplog) if r["event"].startswith("replay.")]
    assert [r["event"] for r in emitted] == ["replay.started", "replay.paused"]
    assert emitted[0]["operation_id"] == emitted[1]["operation_id"]


def test_forecast_screen_worker_result_after_hide_is_private_and_discarded(caplog):
    caplog.set_level(logging.DEBUG)
    host, backend, view = Mock(), Mock(), Mock()
    backend.refresh.return_value = state()
    controller = WeatherScreenController(host, backend, view)
    controller._visible = True
    with patch("controllers.weather.weather_screen_controller.threading.Thread") as worker:
        controller.request_refresh()
        worker.call_args.kwargs["target"](*worker.call_args.kwargs["args"])
    callback = host.schedule_ui_callback.call_args.args[1]
    controller.set_visible(False)
    callback()
    emitted = records(caplog, "weather.screen")
    assert emitted[-1]["event"] == "weather.result_discarded"
    assert emitted[-1]["operation_id"] == emitted[0]["operation_id"]
    view.set_weather_state.assert_not_called()


def test_model_tile_failure_reason_never_retains_error_text(caplog):
    caplog.set_level(logging.INFO)
    controller, _, _, _ = overlay("model")
    controller._frame = RadarFrame(100, PRIVATE)
    controller._tiles.frame_error.return_value = PRIVATE
    controller._wait(0, monotonic(), "tile-operation")
    emitted = records(caplog)
    assert emitted[0]["reason"] == "tile_error"
    assert emitted[0]["operation_id"] == "tile-operation"


def png():
    output = BytesIO()
    Image.new("RGBA", (1, 1), (0, 163, 224, 255)).save(output, format="PNG")
    return output.getvalue()


def test_model_tile_wait_timeout_is_distinct_from_provider_failure(caplog):
    caplog.set_level(logging.INFO)
    controller, _, _, _ = overlay("model")
    controller._frame = RadarFrame(100, PRIVATE)
    controller._wait(0, monotonic() - 181, "tile-operation")
    emitted = records(caplog)
    assert emitted[0]["reason"] == "timeout"
    assert emitted[0]["stage"] == "tiles"
    assert controller._frame is None


def test_tile_download_cache_corruption_failure_and_recovery_are_private(caplog, tmp_path):
    caplog.set_level(logging.DEBUG)
    session = Mock()
    data = png()
    response = Mock(content=data)
    session.get.side_effect = [OSError(PRIVATE), OSError(PRIVATE), response, response]
    with patch("controllers.weather.radar_tile_service.ThreadingHTTPServer"), patch("controllers.weather.radar_tile_service.Thread"):
        service = RadarTileService(cache_root=tmp_path / "private", session=session)
    path = tmp_path / "private" / "42.8028" / "-83.0127.png"
    for _ in range(2):
        with pytest.raises(OSError):
            service._read_or_fetch(path, "https://private.test/?token=private")
    assert service._read_or_fetch(path, PRIVATE) == data
    assert service._read_or_fetch(path, PRIVATE) == data
    path.write_bytes(b"private corrupt PNG")
    assert service._read_or_fetch(path, PRIVATE) == data
    service.close()
    emitted = records(caplog)
    transitions = [r for r in emitted if r["event"] in {"weather.failed", "weather.recovered"}]
    assert [r["event"] for r in transitions] == ["weather.failed", "weather.recovered"]
    assert session.get.call_count == 4
    assert {"tiles.cache_hit", "tiles.cache_invalid", "tiles.cache_miss"} <= {r["event"] for r in emitted}


def test_http_tile_handler_correlates_processing_failure_and_recovery(caplog, tmp_path):
    caplog.set_level(logging.DEBUG)
    with patch("controllers.weather.radar_tile_service.ThreadingHTTPServer") as server, patch("controllers.weather.radar_tile_service.Thread"):
        service = RadarTileService(cache_root=tmp_path, session=Mock())
    handler = object.__new__(server.call_args.args[1])
    handler.path = "/radar/private-location/universal/7/34/47.png?token=private"
    for method in ("send_error", "send_response", "send_header", "end_headers"):
        setattr(handler, method, Mock())
    handler.wfile = Mock()
    service._handle_path = Mock(side_effect=[ValueError(PRIVATE), ValueError(PRIVATE), png()])
    for _ in range(3):
        handler.do_GET()
    emitted = records(caplog)
    transitions = [r for r in emitted if r["event"] in {"weather.failed", "weather.recovered"}]
    assert [r["event"] for r in transitions] == ["weather.failed", "weather.recovered"]
    assert {r["stage"] for r in transitions} == {"tile"}
    requests = [r for r in emitted if r["event"] == "weather.requested"]
    assert transitions[0]["operation_id"] == requests[0]["operation_id"]
    assert transitions[1]["operation_id"] == requests[-1]["operation_id"]
    assert handler.send_error.call_count == 2
    handler.wfile.write.assert_called_once()
