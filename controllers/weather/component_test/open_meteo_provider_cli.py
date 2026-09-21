# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Live Open-Meteo provider component test."""

from __future__ import annotations

import argparse

from controllers.weather.providers import OpenMeteoWeatherProvider
from controllers.weather.weather_state import WeatherLocation


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch live weather through WeatherProviderIf")
    parser.add_argument("--latitude", type=float, required=True)
    parser.add_argument("--longitude", type=float, required=True)
    parser.add_argument("--name", default="Component test location")
    args = parser.parse_args()

    state = OpenMeteoWeatherProvider().refresh(
        WeatherLocation(
            latitude=args.latitude,
            longitude=args.longitude,
            name=args.name,
            source="component-test",
        )
    )

    print("OpenRoadCode Weather Provider Component Test")
    print(f"Provider: {state.source.display_name} ({state.source.provider_id})")
    print(f"Location: {state.location_name}")
    print(f"Position: {state.latitude:.5f}, {state.longitude:.5f}")
    print(f"Temperature: {state.current.temperature_k} K")
    print(f"Feels like: {state.current.apparent_temperature_k} K")
    print(f"Humidity: {state.current.relative_humidity}")
    print(f"Condition: {state.current.condition.value}")
    print(f"Wind: {state.current.wind_speed_m_s} m/s")
    print(f"Hourly forecasts: {len(state.hourly)}")
    print(f"Daily forecasts: {len(state.daily)}")

    if not state.hourly or not state.daily:
        raise RuntimeError("Provider returned incomplete weather state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
