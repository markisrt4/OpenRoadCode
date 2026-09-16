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
    print(f"Temperature: {state.current.get('temperature_2m', '--')}")
    print(f"Feels like: {state.current.get('apparent_temperature', '--')}")
    print(f"Humidity: {state.current.get('relative_humidity_2m', '--')}")
    print(f"Weather code: {state.current.get('weather_code', '--')}")
    print(f"Wind: {state.current.get('wind_speed_10m', '--')}")
    print(f"Hourly points: {len(state.hourly.get('time', []))}")
    print(f"Daily points: {len(state.daily.get('time', []))}")

    if not state.current or not state.hourly or not state.daily:
        raise RuntimeError("Provider returned incomplete weather state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
