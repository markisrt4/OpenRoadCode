# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from datetime import date, datetime

from controllers.weather.weather_presenter import WeatherPresenter
from controllers.weather.weather_state import (
    CurrentWeather,
    DailyForecast,
    HourlyForecast,
    WeatherCondition,
    WeatherSource,
    WeatherState,
)
from ui.weather.weather_ui_stub import WeatherUiStub


def test_presenter_maps_weather_state_without_converting_si_values():
    state = WeatherState(
        latitude=42.8028,
        longitude=-83.0127,
        location_name="Romeo",
        location_source="test",
        source=WeatherSource("open_meteo", "Open-Meteo"),
        fetched_at=123.0,
        current=CurrentWeather(
            temperature_k=292.45,
            apparent_temperature_k=293.35,
            relative_humidity=0.84,
            condition=WeatherCondition.CLOUDY,
            precipitation_m=0.0025,
            pressure_msl_pa=101325.0,
            wind_speed_m_s=2.5,
            wind_direction_deg=270.0,
            wind_gust_m_s=5.0,
        ),
        hourly=(
            HourlyForecast(
                timestamp=datetime(2026, 9, 16, 19),
                temperature_k=291.15,
                precipitation_probability=0.25,
                condition=WeatherCondition.PARTLY_CLOUDY,
                wind_speed_m_s=3.0,
            ),
        ),
        daily=(
            DailyForecast(
                date=date(2026, 9, 17),
                temperature_high_k=295.15,
                temperature_low_k=285.15,
                precipitation_probability=0.4,
                condition=WeatherCondition.RAIN,
                wind_speed_max_m_s=6.0,
            ),
        ),
    )
    ui = WeatherUiStub()
    presenter = WeatherPresenter(ui)

    result = presenter.present(state)

    assert ui.state is result
    assert result.location_name == "Romeo"
    assert result.provider_label == "Open-Meteo"
    assert result.current.temperature_k == 292.45
    assert result.current.pressure_pa == 101325.0
    assert result.current.wind_speed_m_s == 2.5
    assert result.current.condition_label == "Cloudy"
    assert result.hourly[0].temperature_k == 291.15
    assert result.hourly[0].condition_label == "Partly Cloudy"
    assert result.daily[0].temperature_high_k == 295.15
    assert result.daily[0].condition_label == "Rain"
