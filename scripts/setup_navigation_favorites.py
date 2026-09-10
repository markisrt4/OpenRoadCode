#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Interactively geocode and save Home and Work for OpenRoadCode."""

from __future__ import annotations

import math
import os
from pathlib import Path

from controllers.navigation.map_favorites import MapFavorites
from controllers.navigation.sqlite_geocoder import SqliteGeocoder


DEFAULT_SEARCH_DATABASE = (
    Path(os.environ.get("OPENROADCODE_DATA_ROOT", "/srv/openroadcode"))
    / "maps" / "search" / "openroadcode-search.sqlite"
)


def _choose(label: str, geocoder: SqliteGeocoder):
    while True:
        query = input(f"{label} address (blank to skip): ").strip()
        if not query:
            return None
        results = geocoder.geocode(query, limit=5)
        if not results:
            print("  No offline matches found.")
            continue
        print()
        for index, result in enumerate(results, start=1):
            lat = math.degrees(result.position.latitude_rad)
            lon = math.degrees(result.position.longitude_rad)
            print(
                f"  {index}) {result.display_name}\n"
                f"     {lat:.6f}, {lon:.6f}  confidence={result.confidence:.2f}"
            )
        print("  0) Search again")
        raw = input("Select result: ").strip()
        try:
            selected = int(raw)
        except ValueError:
            print("  Enter a number from the list.")
            continue
        if selected == 0:
            continue
        if 1 <= selected <= len(results):
            return results[selected - 1]
        print("  Enter a number from the list.")


def main() -> int:
    if not DEFAULT_SEARCH_DATABASE.is_file():
        raise SystemExit(f"Offline search database is missing: {DEFAULT_SEARCH_DATABASE}")

    favorites = MapFavorites()
    geocoder = SqliteGeocoder(DEFAULT_SEARCH_DATABASE)
    try:
        print("OpenRoadCode Home / Work setup")
        print(f"Offline geocoder: {DEFAULT_SEARCH_DATABASE}")
        print()

        home = _choose("Home", geocoder)
        if home is not None:
            favorites.set_home(home.position)
            print(f"Saved Home: {home.display_name}")
            print()

        work = _choose("Work", geocoder)
        if work is not None:
            favorites.set_work(work.position)
            print(f"Saved Work: {work.display_name}")
            print()
    finally:
        geocoder.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
