# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Probe a real arrival-time forecast independently of routing and the map."""

import argparse
from datetime import datetime, timedelta, timezone

from controllers.route_planning.route_planning_types import GeoPoint
from controllers.weather.route_weather import RouteCheckpoint, RouteWeatherProvider


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--location", nargs=2, type=float, required=True, metavar=("LAT", "LON"))
    parser.add_argument("--hours", type=float, default=1, help="Estimated arrival in hours (default: 1)")
    args = parser.parse_args()
    if not 0 <= args.hours <= 144:
        parser.error("--hours must be between 0 and 144")
    try:
        point = GeoPoint(*args.location)
        arrival = datetime.now(timezone.utc) + timedelta(hours=args.hours)
        forecast = RouteWeatherProvider().forecast((RouteCheckpoint(point, arrival, 0),))[0]
    except Exception as error:
        parser.exit(1, f"Route weather probe failed: {error}\n")
    print("Arrival-time forecast at requested location (not a route)")
    print("Estimated arrival UTC:", arrival.isoformat(timespec="minutes"))
    print("Condition:", forecast.condition)
    for label, value, unit in (("Temperature", forecast.temperature_c, "°C"),
                               ("Precipitation chance", forecast.rain_probability, "%"),
                               ("Wind", forecast.wind_kmh, "km/h")):
        print(f"{label}: unavailable" if value is None else f"{label}: {value:.1f} {unit}")


if __name__ == "__main__":
    main()
