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
    TransitMode.BUS: (" AND class = ?", ("bus",)),
    TransitMode.RAIL: (
        " AND class = ? AND subclass IN (?, ?)",
        ("railway", "station", "halt"),
    ),
    TransitMode.TRAM_SUBWAY: (
        " AND class = ? AND subclass IN (?, ?)",
        ("railway", "tram_stop", "subway_entrance"),
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
        rows = self._connection.execute(
            """
            SELECT id, name, brand, latitude, longitude, class, subclass
              FROM poi
             WHERE category = ?
               AND latitude BETWEEN ? AND ?
               AND longitude BETWEEN ? AND ?
            """ + transit_clause + """
             ORDER BY name COLLATE NOCASE, id
             LIMIT ?
            """,
            (
                category,
                bounds.south,
                bounds.north,
                bounds.west,
                bounds.east,
                *transit_parameters,
                query.limit,
            ),
        ).fetchall()
        return tuple(self._to_poi(row, query.category) for row in rows)

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
