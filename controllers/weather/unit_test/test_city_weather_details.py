# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""City hits must use cached SI details and preserve unrelated map interactions."""
from dataclasses import replace
from unittest.mock import Mock, patch

from controllers.weather.city_weather import CityWeatherHours, WeatherCity
from controllers.weather.city_weather_details import city_details, city_identity
from controllers.weather.city_weather_overlay_controller import CityWeatherOverlayController
from controllers.weather.weather_overlay_controller import WeatherOverlayController
from protocols.map_renderer.map_poi_source import MapPoiSource
from protocols.map_renderer.map_weather_city_source import MapWeatherCitySource, decode_city_click
from ui.weather.weather_overlay_ui_stub import WeatherOverlayUiStub

ANCHOR = 1791028800
CITY = WeatherCity('Detroit', 42.33, -83.05)


def hourly():
    return CityWeatherHours(CITY, tuple(ANCHOR + hour * 3600 for hour in range(-24, 25)),
                            (10,) * 49, (36,) * 49, (1,) * 49)


def controller():
    source = Mock()
    source.poll.return_value = source.poll_selected_city.return_value = None
    sink = WeatherOverlayUiStub()
    backend = CityWeatherOverlayController(Mock(), Mock(), source, Mock(), sink, clock=lambda: ANCHOR)
    backend.enabled = backend._visible = True
    backend._complete(0, (hourly(),), None)
    return backend, sink, source


def test_details_are_si_and_match_selected_snapshot_and_rain_window():
    details = city_details(hourly(), 'future', 6, ANCHOR, ANCHOR)
    assert details.selected_at.timestamp() == ANCHOR + 6 * 3600
    assert details.temperature_k == 283.15 and details.wind_speed_m_s == 10
    assert details.precipitation_m == .006
    assert len(details.hours) == 24
    assert details.hours[0].valid_at.timestamp() == ANCHOR + 3600
    assert details.hours[0].precipitation_m == .001
    assert city_identity(CITY) != city_identity(replace(CITY, latitude=40))


def test_missing_values_are_unavailable_not_zero():
    data = replace(hourly(), temperature_c=(None,) * 49, precipitation_mm=(None,) * 49)
    details = city_details(data, 'past', 24, ANCHOR, ANCHOR)
    assert details.temperature_k is None and details.precipitation_m is None
    assert details.hours[0].temperature_k is None


def test_click_selection_uses_cache_pauses_city_playback_and_dismisses():
    backend, sink, source = controller()
    backend.playing = True
    source.poll_selected_city.side_effect = [city_identity(CITY), None]
    backend._poll(backend._poll_generation)
    assert sink.city_state.details.name == 'Detroit'
    assert not backend.playing
    backend._provider.hourly.assert_not_called()
    backend.select(period='future', hours=6)
    assert sink.city_state.details.selected_at.timestamp() == ANCHOR + 6 * 3600
    backend.select_details(None)
    assert sink.city_state.details is None


def test_unknown_city_and_hidden_or_disabled_clicks_do_not_open():
    backend, sink, _ = controller()
    backend.select_details('weather-city:unknown')
    assert sink.city_state.details is None
    backend.select_details(city_identity(CITY))
    backend.hide()
    backend.select_details(city_identity(CITY))
    assert sink.city_state.details is None
    backend._visible = True
    backend.set_enabled(False)
    backend.select_details(city_identity(CITY))
    assert sink.city_state.details is None


def test_reopening_discards_queued_hidden_clicks():
    backend, sink, source = controller()
    backend.hide()
    source.poll_selected_city.side_effect = [city_identity(CITY), None, None]
    backend.show()
    assert sink.city_state.details is None


def test_weather_click_adapter_routes_only_weather_features():
    identity = city_identity(CITY)
    payload = {'marker_id': identity, 'latitude': 42.33, 'longitude': -83.05, 'selection_radius_m': 50}
    assert decode_city_click(payload) == identity
    assert decode_city_click({'marker_id': 'poi:one'}) is None
    assert decode_city_click({'marker_id': None}) is None
    assert MapPoiSource._decode_click(payload) is None
    assert MapPoiSource._decode_click({**payload, 'marker_id': 'poi:one'}) is not None
    subscriber = Mock()
    subscriber.receive.side_effect = [('map.click', payload), RuntimeError('closed')]
    with patch('protocols.map_renderer.map_weather_city_source.Thread'):
        source = MapWeatherCitySource(subscriber)
    source._receive()
    assert source.poll_selected_city() == identity
    assert source.poll_selected_city() is None and source.poll() is None
    source.close()
    subscriber.close.assert_called_once()


def test_semantic_request_handler_forwards_city_selection_and_dismissal():
    city = Mock()
    handler = WeatherOverlayController(Mock(), city, Mock(), Mock())
    handler.request_city_details(city_identity(CITY))
    city.select_details.assert_called_once_with(city_identity(CITY))
    handler.request_city_details(None)
    assert city.select_details.call_args.args == (None,)


def test_close_clears_details_and_rejects_late_click_callbacks():
    backend, sink, source = controller()
    backend.select_details(city_identity(CITY))
    generation = backend._poll_generation
    backend.close()
    assert sink.city_state.details is None and not sink.city_state.visible
    source.poll_selected_city.side_effect = [city_identity(CITY), None]
    backend._poll(generation)
    backend.select_details(city_identity(CITY))
    assert sink.city_state.details is None
    backend.close()
    backend._provider.close.assert_called_once()
