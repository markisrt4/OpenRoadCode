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


_CATEGORY_SQL: dict[PoiCategory, tuple[str, ...]] = {
    PoiCategory.FOOD: ("restaurant", "fast_food", "cafe", "food"),
    PoiCategory.FUEL: ("fuel", "gas_station"),
    PoiCategory.GROCERY: ("grocery", "supermarket", "convenience"),
    PoiCategory.TRANSIT: (
        "bus",
        "bus_stop",
        "station",
        "railway_station",
        "tram_stop",
        "subway",
        "subway_entrance",
    ),
}


class SqlitePoiSearchSource(PoiSearchSourceIf):
    """Search an OpenRoadCode POI sidecar database by geographic bounds."""

    def __init__(self, database_path: str | Path) -> None:
        self._path = Path(database_path).expanduser()
        self._connection = sqlite3.connect(self._path)
        self._connection.row_factory = sqlite3.Row

    def search(self, query: PoiSearchQuery) -> tuple[PointOfInterest, ...]:
        values = _CATEGORY_SQL.get(query.category)
        if not values:
            return ()

        placeholders = ",".join("?" for _ in values)
        category_clause = (
            f"(lower(coalesce(class, '')) IN ({placeholders}) "
            f"OR lower(coalesce(subclass, '')) IN ({placeholders}))"
        )
        bounds = query.bounds
        sql = f"""
            SELECT id, name, brand, latitude, longitude, class, subclass
              FROM poi
             WHERE latitude BETWEEN ? AND ?
               AND longitude BETWEEN ? AND ?
               AND {category_clause}
             ORDER BY name COLLATE NOCASE, id
             LIMIT ?
        """
        parameters = (
            bounds.south,
            bounds.north,
            bounds.west,
            bounds.east,
            *values,
            *values,
            query.limit,
        )
        rows = self._connection.execute(sql, parameters).fetchall()
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
