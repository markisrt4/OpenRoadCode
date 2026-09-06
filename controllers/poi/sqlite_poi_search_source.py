# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""SQLite-backed offline POI search source."""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path

from controllers.poi.poi_models import PoiCategory, PointOfInterest
from controllers.poi.poi_search_source_if import PoiSearchQuery, PoiSearchSourceIf
from ui.navigation import GeoPoint


_CATEGORY_NAME: dict[PoiCategory, str] = {
    PoiCategory.FOOD: "FOOD",
    PoiCategory.FUEL: "FUEL",
    PoiCategory.GROCERY: "GROCERY",
    PoiCategory.TRANSIT: "TRANSIT",
}


class SqlitePoiSearchSource(PoiSearchSourceIf):
    """Search the unified OpenRoadCode offline search database."""

    def __init__(self, database_path: str | Path) -> None:
        self._path = Path(database_path).expanduser()
        self._connection = sqlite3.connect(
            f"file:{self._path}?mode=ro",
            uri=True,
        )
        self._connection.row_factory = sqlite3.Row

    def search(self, query: PoiSearchQuery) -> tuple[PointOfInterest, ...]:
        category = _CATEGORY_NAME.get(query.category)
        if category is None:
            return ()

        bounds = query.bounds
        rows = self._connection.execute(
            """
            SELECT id, name, brand, latitude, longitude, class, subclass
              FROM poi
             WHERE category = ?
               AND latitude BETWEEN ? AND ?
               AND longitude BETWEEN ? AND ?
             ORDER BY name COLLATE NOCASE, id
             LIMIT ?
            """,
            (
                category,
                bounds.south,
                bounds.north,
                bounds.west,
                bounds.east,
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
