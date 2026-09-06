# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math
import sqlite3

from controllers.poi import PoiCategory, PoiSearchBounds, PoiSearchQuery
from controllers.poi.sqlite_poi_search_source import SqlitePoiSearchSource


def _database(tmp_path):
    path = tmp_path / "openroadcode-search.sqlite"
    connection = sqlite3.connect(path)
    connection.execute(
        """CREATE TABLE poi (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            brand TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            category TEXT NOT NULL,
            class TEXT,
            subclass TEXT
        )"""
    )
    connection.executemany(
        "INSERT INTO poi VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("restaurant", "Lunch", None, 42.50, -83.05, "FOOD", "restaurant", "restaurant"),
            ("fuel", "Fuel", None, 42.51, -83.04, "FUEL", "shop", "fuel"),
            ("bus", "12 Mile / Ryan", None, 42.52, -83.03, "TRANSIT", "bus", "bus_stop"),
            ("far", "Far Away", None, 44.00, -83.03, "TRANSIT", "bus", "bus_stop"),
        ],
    )
    connection.commit()
    connection.close()
    return path


def _query(category: PoiCategory) -> PoiSearchQuery:
    return PoiSearchQuery(
        category=category,
        bounds=PoiSearchBounds(42.0, -84.0, 43.0, -82.0),
    )


def test_search_is_bounded_and_category_specific(tmp_path) -> None:
    source = SqlitePoiSearchSource(_database(tmp_path))
    try:
        results = source.search(_query(PoiCategory.FUEL))
    finally:
        source.close()
    assert [poi.name for poi in results] == ["Fuel"]
    assert math.isclose(math.degrees(results[0].position.latitude_rad), 42.51)


def test_public_transit_matches_bus_stop_schema(tmp_path) -> None:
    source = SqlitePoiSearchSource(_database(tmp_path))
    try:
        results = source.search(_query(PoiCategory.TRANSIT))
    finally:
        source.close()
    assert [poi.name for poi in results] == ["12 Mile / Ryan"]
    assert results[0].source_class == "bus"
    assert results[0].source_subclass == "bus_stop"
