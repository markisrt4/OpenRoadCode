# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Probe one city through the same hourly data path as the TV-style map."""

import argparse
from datetime import datetime, timezone
from time import time

from controllers.weather.city_weather import CityWeatherProvider, WeatherCity, city_label, city_value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--location', type=float, nargs=2, default=(42.3314, -83.0458), metavar=('LAT', 'LON'))
    parser.add_argument('--name', default='Detroit')
    parser.add_argument('--kind', choices=('temperature', 'wind', 'precipitation'), default='temperature')
    parser.add_argument('--period', choices=('past', 'future'), default='past')
    parser.add_argument('--hours', type=int, choices=range(1, 25), default=1)
    parser.add_argument('--metric', action='store_true')
    args = parser.parse_args()
    provider = CityWeatherProvider()
    try:
        weather, = provider.hourly((WeatherCity(args.name, *args.location),))
        anchor = int(time() // 3600) * 3600
        value = city_value(weather, args.kind, args.hours, args.period, anchor)
        print(f'{weather.city.name}: {city_label(value, args.kind, not args.metric)}')
        print(f'{args.kind} · {args.period} · {args.hours}h · anchor {datetime.fromtimestamp(anchor).astimezone().isoformat()}')
        print('Source: Open-Meteo · Model estimates, not weather-station observations')
        print(f'Hourly coverage UTC: {datetime.fromtimestamp(weather.times[0], timezone.utc).isoformat()} to '
              f'{datetime.fromtimestamp(weather.times[-1], timezone.utc).isoformat()}')
        if value is None:
            print('Selected hour/window is missing data; the map will show —')
            return 1
        return 0
    except Exception as error:
        print(f'City weather probe failed: {error}')
        return 1
    finally:
        provider.close()


if __name__ == '__main__':
    raise SystemExit(main())
