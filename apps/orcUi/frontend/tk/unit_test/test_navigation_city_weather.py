# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""City weather must stay separate from radar and reject obsolete viewport results."""

from unittest.mock import Mock

from common.units.unit_system import UnitSystem
from controllers.weather.city_weather import CityWeatherHours, WeatherCity
from apps.orcUi.frontend.tk.navigation_city_weather import NavigationCityWeather
from protocols.map_renderer.map_weather_city_source import RawWeatherCity, decode_city_result

ANCHOR = 1791028800
CITY = WeatherCity("Detroit", 42.33, -83.05)


def component():
    source = Mock()
    source.poll.return_value = None
    ui = NavigationCityWeather(Mock(), Mock(), lambda: UnitSystem.IMPERIAL,
                               provider=Mock(), source=source, clock=lambda: ANCHOR)
    ui._visible = True
    return ui


def weather():
    return (CityWeatherHours(CITY, tuple(ANCHOR + h * 3600 for h in range(-24, 25)),
                             (0,) * 49, (16.09344,) * 49, (25.4,) * 49),)


def test_label_field_and_units_change_locally_without_resetting_radar_route_or_camera():
    ui = component()
    ui.enabled = True
    ui._complete(0, weather(), None)
    assert ui._renderer.set_city_weather.call_args.args[0]['features'][0]['properties']['value'] == '32°F'
    ui.select(kind='wind', hours=24, period='future')
    assert ui._renderer.set_city_weather.call_args.args[0]['features'][0]['properties']['value'] == '10 mph'
    ui.select(kind='precipitation', hours=2)
    feature = ui._renderer.set_city_weather.call_args.args[0]['features'][0]
    assert feature['properties']['value'] == '2.00"'
    assert feature['properties']['name'] == 'Detroit'
    assert feature['geometry']['coordinates'] == [-83.05, 42.33]
    ui._provider.hourly.assert_not_called()
    ui._renderer.set_camera.assert_not_called()
    ui._renderer.set_weather_field.assert_not_called()
    ui._renderer.set_weather_radar.assert_not_called()
    ui._renderer.set_route_weather.assert_not_called()


def test_late_previous_viewport_weather_cannot_replace_current_labels():
    ui = component()
    ui.enabled = True
    ui._visible = True
    ui._generation = 2
    ui.refresh = Mock()
    ui._complete(1, weather(), None)
    assert ui._weather == ()
    ui.refresh.assert_called_once()
    ui._renderer.set_city_weather.assert_not_called()


def test_off_and_closed_reject_late_weather_and_clear_labels():
    ui = component()
    ui.set_enabled(False)
    ui._complete(0, weather(), None)
    assert ui._weather == ()
    assert ui._renderer.set_city_weather.call_args.args[0]['features'] == []
    ui.close()
    ui._complete(ui._generation, weather(), None)
    ui._provider.close.assert_called_once()
    ui._source.close.assert_called_once()


def test_failed_refresh_clears_stale_numbers_and_stops_playback():
    ui = component()
    ui.enabled = True
    ui._visible = True
    ui._complete(0, weather(), None)
    ui.set_playing(True)
    ui._complete(0, (), 'no connection')
    assert not ui.playing and ui._weather == ()
    assert 'unavailable' in ui.status
    assert ui._renderer.set_city_weather.call_args.args[0]['features'] == []


def test_history_plays_toward_now_but_precipitation_accumulations_grow():
    ui = component()
    ui.enabled = True
    ui._visible = True
    ui._complete(0, weather(), None)
    ui.select(hours=24)
    ui.set_playing(True)
    generation = ui._play_generation
    ui._advance(generation)
    assert ui.hours == 23
    ui.select(kind='precipitation', hours=1)
    ui._advance(generation)
    assert ui.hours == 2
    ui.hide()
    ui._advance(generation)
    assert not ui.playing and ui.hours == 2


def test_queued_old_playback_tick_does_not_run_after_play_pause_play():
    ui = component()
    ui.enabled = True
    ui._visible = True
    ui._complete(0, weather(), None)
    ui.set_playing(True)
    old_tick = ui._host.schedule_ui_callback.call_args.args[1]
    ui.set_playing(False)
    ui.set_playing(True)
    old_tick()
    assert ui.hours == 1


def test_cached_viewport_does_not_make_another_api_request_and_ignores_old_reply_ids():
    ui = component()
    ui.enabled = True
    ui._complete(0, weather(), None)
    ui._cities = ()
    ui._pending_id = 3
    ui._source.poll.side_effect = [(2, (WeatherCity('Old', 1, 2),)), (3, (CITY,)), None]
    ui.refresh = Mock()
    ui._drain_cities()
    assert ui._cities == (CITY,)
    assert ui._weather == weather()
    ui.refresh.assert_not_called()


def test_missing_city_names_provide_zoom_hint_and_clear_overlay():
    ui = component()
    ui.enabled = True
    ui._pending_id = 1
    ui._source.poll.side_effect = [(1, ()), None]
    ui._drain_cities()
    assert 'zoom out' in ui.status


def test_hourly_caption_includes_selected_period_and_precipitation_window():
    ui = component()
    ui._anchor = ANCHOR
    assert '1h ago' in ui.time_label()
    ui.select(hours=24, period='future', kind='precipitation')
    assert '24h total' in ui.time_label() and '→' in ui.time_label()


def test_city_reply_validation_drops_invalid_coordinates_and_duplicates():
    good = {'name': 'Detroit', 'latitude': 42.33, 'longitude': -83.05}
    reply = decode_city_result({'request_id': 1, 'cities': [good, good, dict(good, latitude=float('nan')),
                                                        dict(good, longitude=181), dict(good, name='')]})
    assert reply == (1, (RawWeatherCity(CITY.name, CITY.latitude, CITY.longitude),))
    assert decode_city_result({'request_id': True, 'cities': [good]}) is None


def test_hidden_navigation_cannot_publish_city_numbers_over_the_home_map():
    ui = component()
    ui.enabled = True
    ui._complete(0, weather(), None)
    ui.hide()
    assert ui._renderer.set_city_weather.call_args.args[0]['features'] == []
    ui._complete(0, weather(), None)
    assert ui._renderer.set_city_weather.call_args.args[0]['features'] == []
    ui.show()
    assert ui._renderer.set_city_weather.call_args.args[0]['features']
