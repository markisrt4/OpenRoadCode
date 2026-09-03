# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise the offline POI search source without starting a UI or renderer."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from controllers.poi import PoiCategory, PoiSearchBounds, PoiSearchQuery
from controllers.poi.sqlite_poi_search_source import SqlitePoiSearchSource

_DEFAULT_DATABASE = Path.home() / ".local/share/openroadcode/maps/poi/openroadcode-poi.sqlite"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("category", choices=("food", "fuel", "grocery", "transit"))
    parser.add_argument("--database", type=Path, default=_DEFAULT_DATABASE)
    parser.add_argument("--south", type=float, required=True)
    parser.add_argument("--west", type=float, required=True)
    parser.add_argument("--north", type=float, required=True)
    parser.add_argument("--east", type=float, required=True)
    parser.add_argument("--limit", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    query = PoiSearchQuery(
        category=PoiCategory[args.category.upper()],
        bounds=PoiSearchBounds(args.south, args.west, args.north, args.east),
        limit=args.limit,
    )
    source = SqlitePoiSearchSource(args.database)
    try:
        results = source.search(query)
    finally:
        source.close()

    print(f"{len(results)} {args.category} POIs")
    for poi in results:
        latitude = math.degrees(poi.position.latitude_rad)
        longitude = math.degrees(poi.position.longitude_rad)
        print(
            f'{latitude:.6f},{longitude:.6f}  {poi.name}  '
            f'class={poi.source_class or ""} subclass={poi.source_subclass or ""}'
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
