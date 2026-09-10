# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math
import sqlite3

from controllers.poi import PoiCategory, PoiSearchBounds, PoiSearchQuery, TransitMode
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
            subclass TEXT,
            transit_mode TEXT
        )"""
    )
    connection.executemany(
        "INSERT INTO poi VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("restaurant", "Lunch", None, 42.50, -83.05, "food", "restaurant", "restaurant", None),
            ("fuel", "Fuel", None, 42.51, -83.04, "fuel", "shop", "fuel", None),
            ("bus", "12 Mile / Ryan", None, 42.52, -83.03, "transit", "bus", "bus_stop", "bus"),
            ("rail", "Central Station", None, 42.53, -83.02, "transit", "public_transport", "station", "rail"),
            ("tram", "Streetcar Stop", None, 42.54, -83.01, "transit", "public_transport", "stop_position", "tram"),
            ("subway", "Subway Stop", None, 42.55, -83.00, "transit", "public_transport", "station", "subway"),
            ("unknown", "Unknown Transit", None, 42.56, -82.99, "transit", "public_transport", "platform", None),
            ("far", "Far Away", None, 44.00, -83.03, "transit", "bus", "bus_stop", "bus"),
        ],
    )
    connection.commit()
    connection.close()
    return path


def _query(category: PoiCategory, transit_mode: TransitMode = TransitMode.ALL) -> PoiSearchQuery:
    return PoiSearchQuery(
        category=category,
        bounds=PoiSearchBounds(42.0, -84.0, 43.0, -82.0),
        transit_mode=transit_mode,
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
        results = source.search(_query(PoiCategory.TRANSIT, TransitMode.BUS))
    finally:
        source.close()
    assert [poi.name for poi in results] == ["12 Mile / Ryan"]
    assert results[0].source_class == "bus"
    assert results[0].source_subclass == "bus_stop"


def test_transit_modes_use_normalized_mode_column(tmp_path) -> None:
    source = SqlitePoiSearchSource(_database(tmp_path))
    try:
        rail = source.search(_query(PoiCategory.TRANSIT, TransitMode.RAIL))
        tram_subway = source.search(_query(PoiCategory.TRANSIT, TransitMode.TRAM_SUBWAY))
        all_transit = source.search(_query(PoiCategory.TRANSIT, TransitMode.ALL))
    finally:
        source.close()

    assert [poi.name for poi in rail] == ["Central Station"]
    assert {poi.name for poi in tram_subway} == {"Streetcar Stop", "Subway Stop"}
    assert "Unknown Transit" in {poi.name for poi in all_transit}


def test_limit_prefers_nearest_pois_instead_of_alphabetical_order(tmp_path) -> None:
    path = _database(tmp_path)
    connection = sqlite3.connect(path)
    connection.executemany(
        "INSERT INTO poi VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("near-z", "Zulu Nearby", None, 42.5005, -83.0005, "food", "restaurant", "restaurant", None),
            ("far-a", "Alpha Far", None, 42.90, -83.80, "food", "restaurant", "restaurant", None),
        ],
    )
    connection.commit()
    connection.close()

    source = SqlitePoiSearchSource(path)
    try:
        results = source.search(
            PoiSearchQuery(
                category=PoiCategory.FOOD,
                bounds=PoiSearchBounds(42.0, -84.0, 43.0, -82.0),
                limit=1,
            )
        )
    finally:
        source.close()

    assert [poi.name for poi in results] == ["Zulu Nearby"]
