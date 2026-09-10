# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise the offline POI search source without starting a UI or renderer."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from controllers.poi import (
    PoiCategory,
    PoiSearchBounds,
    PoiSearchQuery,
    TransitMode,
)
from controllers.poi.sqlite_poi_search_source import SqlitePoiSearchSource

_EARTH_RADIUS_M = 6_378_137.0
_DEFAULT_DATABASE = Path("/srv/openroadcode/maps/search/openroadcode-search.sqlite")

_TRANSIT_MODES = {
    "all": TransitMode.ALL,
    "bus": TransitMode.BUS,
    "rail": TransitMode.RAIL,
    "tram-subway": TransitMode.TRAM_SUBWAY,
}


def _bounds_from_center(latitude: float, longitude: float, radius_km: float) -> PoiSearchBounds:
    radius_m = radius_km * 1000.0
    latitude_delta = math.degrees(radius_m / _EARTH_RADIUS_M)
    cos_latitude = max(1.0e-6, abs(math.cos(math.radians(latitude))))
    longitude_delta = math.degrees(radius_m / (_EARTH_RADIUS_M * cos_latitude))
    return PoiSearchBounds(
        south=max(-90.0, latitude - latitude_delta),
        west=max(-180.0, longitude - longitude_delta),
        north=min(90.0, latitude + latitude_delta),
        east=min(180.0, longitude + longitude_delta),
    )


def _distance_km(
    latitude: float,
    longitude: float,
    poi_latitude: float,
    poi_longitude: float,
) -> float:
    lat1 = math.radians(latitude)
    lat2 = math.radians(poi_latitude)
    dlat = lat2 - lat1
    dlon = math.radians(poi_longitude - longitude)
    haversine = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    )
    return (
        2.0
        * _EARTH_RADIUS_M
        * math.asin(min(1.0, math.sqrt(haversine)))
        / 1000.0
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("category", choices=("food", "fuel", "grocery", "transit"))
    parser.add_argument("--database", type=Path, default=_DEFAULT_DATABASE)
    parser.add_argument(
        "--lat",
        type=float,
        required=True,
        help="search-center latitude in degrees",
    )
    parser.add_argument(
        "--lon",
        type=float,
        required=True,
        help="search-center longitude in degrees",
    )
    parser.add_argument(
        "--radius-km",
        type=float,
        default=20.0,
        help="bounding search radius in km (default: 20)",
    )
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument(
        "--transit-mode",
        choices=tuple(_TRANSIT_MODES),
        default="all",
        help="transit subtype filter: all, bus, rail, or tram-subway (default: all)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not -90.0 <= args.lat <= 90.0:
        raise SystemExit("--lat must be between -90 and 90")
    if not -180.0 <= args.lon <= 180.0:
        raise SystemExit("--lon must be between -180 and 180")
    if args.radius_km <= 0:
        raise SystemExit("--radius-km must be positive")
    if args.limit <= 0:
        raise SystemExit("--limit must be positive")
    if args.category != "transit" and args.transit_mode != "all":
        raise SystemExit("--transit-mode is only valid with the transit category")

    query = PoiSearchQuery(
        category=PoiCategory[args.category.upper()],
        bounds=_bounds_from_center(args.lat, args.lon, args.radius_km),
        limit=args.limit,
        transit_mode=_TRANSIT_MODES[args.transit_mode],
    )
    source = SqlitePoiSearchSource(args.database)
    try:
        results = source.search(query)
    finally:
        source.close()

    mode_suffix = ""
    if args.category == "transit":
        mode_suffix = f" mode={args.transit_mode}"
    print(
        f"{len(results)} {args.category} POIs{mode_suffix} near "
        f"{args.lat:.6f},{args.lon:.6f} within {args.radius_km:g} km bounding radius"
    )
    for poi in results:
        latitude = math.degrees(poi.position.latitude_rad)
        longitude = math.degrees(poi.position.longitude_rad)
        distance_km = _distance_km(args.lat, args.lon, latitude, longitude)
        print(
            f"{distance_km:6.2f} km  {latitude:.6f},{longitude:.6f}  {poi.name}  "
            f'class={poi.source_class or ""} subclass={poi.source_subclass or ""}'
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
