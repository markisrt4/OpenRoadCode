# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""SQLite-backed offline POI search source."""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path

from controllers.poi.poi_models import PoiCategory, PointOfInterest, TransitMode
from controllers.poi.poi_search_source_if import PoiSearchQuery, PoiSearchSourceIf
from ui.navigation import GeoPoint


_CATEGORY_NAME: dict[PoiCategory, str] = {
    PoiCategory.FOOD: "food",
    PoiCategory.FUEL: "fuel",
    PoiCategory.GROCERY: "grocery",
    PoiCategory.TRANSIT: "transit",
}

_TRANSIT_SQL: dict[TransitMode, tuple[str, tuple[str, ...]]] = {
    TransitMode.ALL: ("", ()),
    TransitMode.BUS: (" AND transit_mode = ?", ("bus",)),
    TransitMode.RAIL: (" AND transit_mode = ?", ("rail",)),
    TransitMode.TRAM_SUBWAY: (
        " AND transit_mode IN (?, ?)",
        ("tram", "subway"),
    ),
}


class SqlitePoiSearchSource(PoiSearchSourceIf):
    """Search the unified OpenRoadCode offline search database."""

    def __init__(self, database_path: str | Path) -> None:
        self._path = Path(database_path).expanduser()
        self._connection = sqlite3.connect(f"file:{self._path}?mode=ro", uri=True)
        self._connection.row_factory = sqlite3.Row

    def search(self, query: PoiSearchQuery) -> tuple[PointOfInterest, ...]:
        category = _CATEGORY_NAME.get(query.category)
        if category is None:
            return ()

        transit_clause = ""
        transit_parameters: tuple[str, ...] = ()
        if query.category is PoiCategory.TRANSIT:
            transit_clause, transit_parameters = _TRANSIT_SQL[query.transit_mode]

        bounds = query.bounds
        center_latitude = (bounds.south + bounds.north) / 2.0
        center_longitude = (bounds.west + bounds.east) / 2.0
        longitude_scale = math.cos(math.radians(center_latitude))

        fetch_limit = query.limit * 4 if query.category is PoiCategory.TRANSIT else query.limit
        rows = self._connection.execute(
            """
            SELECT id, name, brand, latitude, longitude, class, subclass
              FROM poi
             WHERE category = ?
               AND latitude BETWEEN ? AND ?
               AND longitude BETWEEN ? AND ?
            """
            + transit_clause
            + """
             ORDER BY
                 ((latitude - ?) * (latitude - ?)) +
                 (((longitude - ?) * ?) * ((longitude - ?) * ?)),
                 name COLLATE NOCASE,
                 id
             LIMIT ?
            """,
            (
                category,
                bounds.south,
                bounds.north,
                bounds.west,
                bounds.east,
                *transit_parameters,
                center_latitude,
                center_latitude,
                center_longitude,
                longitude_scale,
                center_longitude,
                longitude_scale,
                fetch_limit,
            ),
        ).fetchall()
        pois = tuple(self._to_poi(row, query.category) for row in rows)
        if query.category is PoiCategory.TRANSIT:
            pois = _dedupe_transit(pois)
        return pois[: query.limit]

    def close(self) -> None:
        self._connection.close()

    @staticmethod
    def _to_poi(row: sqlite3.Row, category: PoiCategory) -> PointOfInterest:
        return PointOfInterest(
            poi_id=str(row["id"]),
            name=str(row["name"] or "Unnamed POI"),
            category=category,
            position=GeoPoint(
                math.radians(float(row["latitude"])),
                math.radians(float(row["longitude"])),
            ),
            brand=row["brand"],
            source_class=row["class"],
            source_subclass=row["subclass"],
        )


def _dedupe_transit(
    pois: tuple[PointOfInterest, ...],
    *,
    distance_threshold_m: float = 75.0,
) -> tuple[PointOfInterest, ...]:
    """Collapse multiple OSM representations of the same physical transit stop."""

    kept: list[PointOfInterest] = []
    for poi in pois:
        normalized_name = " ".join(poi.name.casefold().split())
        duplicate = False
        for existing in kept:
            if " ".join(existing.name.casefold().split()) != normalized_name:
                continue
            if _distance_m(existing.position, poi.position) <= distance_threshold_m:
                duplicate = True
                break
        if not duplicate:
            kept.append(poi)
    return tuple(kept)


def _distance_m(first: GeoPoint, second: GeoPoint) -> float:
    dlat = second.latitude_rad - first.latitude_rad
    dlon = second.longitude_rad - first.longitude_rad
    haversine = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(first.latitude_rad)
        * math.cos(second.latitude_rad)
        * math.sin(dlon / 2.0) ** 2
    )
    return 2.0 * 6_378_137.0 * math.asin(min(1.0, math.sqrt(haversine)))
