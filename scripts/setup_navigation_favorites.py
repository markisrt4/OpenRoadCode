#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Interactively geocode and save Home and Work for OpenRoadCode."""

from __future__ import annotations

import math
import os
from pathlib import Path

from controllers.cache import PersistentCache
from controllers.navigation.map_favorites import MapFavorite, MapFavorites
from controllers.navigation.position_snapshot_cache import (
    DEFAULT_POSITION_CACHE_DIRECTORY,
    PositionSnapshotCache,
)
from controllers.navigation.sqlite_geocoder import SqliteGeocoder
from ui.navigation import GeoPoint


DEFAULT_SEARCH_DATABASE = (
    Path(os.environ.get("OPENROADCODE_DATA_ROOT", "/srv/openroadcode"))
    / "maps" / "search" / "openroadcode-search.sqlite"
)


def _format_favorite(favorite: MapFavorite | None) -> str:
    if favorite is None:
        return "not configured"
    lat = math.degrees(favorite.position.latitude_rad)
    lon = math.degrees(favorite.position.longitude_rad)
    return f"{favorite.name}: {lat:.6f}, {lon:.6f}"


def _cached_position() -> GeoPoint | None:
    state = PositionSnapshotCache(
        PersistentCache(DEFAULT_POSITION_CACHE_DIRECTORY)
    ).load()
    if (
        state is None
        or not state.has_fix
        or state.latitude_deg is None
        or state.longitude_deg is None
    ):
        return None
    return GeoPoint(
        latitude_rad=math.radians(state.latitude_deg),
        longitude_rad=math.radians(state.longitude_deg),
        altitude_m=state.altitude_m,
    )


def _manual_position() -> GeoPoint | None:
    raw = input("Latitude,longitude (blank to cancel): ").strip()
    if not raw:
        return None
    try:
        latitude_text, longitude_text = raw.split(",", 1)
        latitude = float(latitude_text.strip())
        longitude = float(longitude_text.strip())
    except ValueError:
        print("  Enter coordinates as latitude,longitude.")
        return None
    if not -90.0 <= latitude <= 90.0 or not -180.0 <= longitude <= 180.0:
        print("  Coordinates are out of range.")
        return None
    return GeoPoint(math.radians(latitude), math.radians(longitude))


def _search_address(label: str, geocoder: SqliteGeocoder) -> GeoPoint | None:
    while True:
        query = input(f"{label} address (blank to cancel): ").strip()
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
            qualifier = "exact address" if result.source == "address" else (
                "approximate street location" if result.source == "street" else result.source
            )
            print(
                f"  {index}) {result.display_name}\n"
                f"     {lat:.6f}, {lon:.6f}  {qualifier}  confidence={result.confidence:.2f}"
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
            return results[selected - 1].position
        print("  Enter a number from the list.")


def _choose_position(
    label: str,
    current: MapFavorite | None,
    geocoder: SqliteGeocoder,
) -> GeoPoint | None:
    while True:
        print()
        print(f"{label}: {_format_favorite(current)}")
        print("  1) Search by address")
        print("  2) Use last known position")
        print("  3) Enter latitude / longitude")
        print("  4) Keep existing")
        choice = input("Select option: ").strip()

        if choice == "1":
            position = _search_address(label, geocoder)
            if position is not None:
                return position
        elif choice == "2":
            position = _cached_position()
            if position is None:
                print("  No cached position fix is available.")
                continue
            lat = math.degrees(position.latitude_rad)
            lon = math.degrees(position.longitude_rad)
            print(f"  Using last known position: {lat:.6f}, {lon:.6f}")
            return position
        elif choice == "3":
            position = _manual_position()
            if position is not None:
                return position
        elif choice == "4":
            return current.position if current is not None else None
        else:
            print("  Enter 1, 2, 3, or 4.")


def main() -> int:
    if not DEFAULT_SEARCH_DATABASE.is_file():
        raise SystemExit(f"Offline search database is missing: {DEFAULT_SEARCH_DATABASE}")

    favorites = MapFavorites()
    geocoder = SqliteGeocoder(DEFAULT_SEARCH_DATABASE)
    try:
        print("OpenRoadCode Home / Work setup")
        print(f"Offline geocoder: {DEFAULT_SEARCH_DATABASE}")
        print()

        home = _choose_position("Home", favorites.home, geocoder)
        if home is not None and (favorites.home is None or home != favorites.home.position):
            favorites.set_home(home)
            print("Saved Home.")

        work = _choose_position("Work", favorites.work, geocoder)
        if work is not None and (favorites.work is None or work != favorites.work.position):
            favorites.set_work(work)
            print("Saved Work.")
    finally:
        geocoder.close()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nOpenRoadCode Home / Work setup cancelled.")
        raise SystemExit(130)
