# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math
import sqlite3

from controllers.navigation.sqlite_geocoder import SqliteGeocoder


def _db(tmp_path):
    path = tmp_path / "search.sqlite"
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE address (
            id TEXT PRIMARY KEY, house_number TEXT, street TEXT, unit TEXT,
            city TEXT, state TEXT, postcode TEXT, country TEXT,
            latitude REAL NOT NULL, longitude REAL NOT NULL
        );
        CREATE TABLE street (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, city TEXT, state TEXT,
            postcode TEXT, latitude REAL NOT NULL, longitude REAL NOT NULL
        );
        CREATE TABLE place (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT, state TEXT,
            country TEXT, latitude REAL NOT NULL, longitude REAL NOT NULL
        );
    """)
    con.execute(
        "INSERT INTO address VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("a1","123","Main Street",None,"Romeo","MI","48065","US",42.8028,-83.0127),
    )
    con.execute(
        "INSERT INTO street VALUES (?,?,?,?,?,?,?)",
        ("s1","Main Street","Romeo","MI","48065",42.8030,-83.0130),
    )
    con.execute(
        "INSERT INTO place VALUES (?,?,?,?,?,?,?)",
        ("p1","Romeo","village","MI","US",42.8028,-83.0127),
    )
    con.commit()
    con.close()
    return path


def test_exact_address_is_ranked_first(tmp_path):
    geocoder = SqliteGeocoder(_db(tmp_path))
    try:
        results = geocoder.geocode("123 Main Street, Romeo, MI 48065")
    finally:
        geocoder.close()
    assert results
    assert results[0].source == "address"
    assert results[0].confidence == 1.0
    assert results[0].display_name.startswith("123 Main Street")
    assert math.isclose(math.degrees(results[0].position.latitude_rad), 42.8028)


def test_street_fallback_is_available_when_house_number_missing(tmp_path):
    geocoder = SqliteGeocoder(_db(tmp_path))
    try:
        results = geocoder.geocode("Main Street, Romeo, MI 48065")
    finally:
        geocoder.close()
    assert results
    assert results[0].source == "street"


def test_place_search_resolves_named_place(tmp_path):
    geocoder = SqliteGeocoder(_db(tmp_path))
    try:
        results = geocoder.geocode("Romeo")
    finally:
        geocoder.close()
    assert any(result.source == "place" for result in results)
