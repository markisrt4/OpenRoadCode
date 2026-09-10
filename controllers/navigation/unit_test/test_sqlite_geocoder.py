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


def test_street_suffix_abbreviation_matches_full_suffix(tmp_path):
    path = _db(tmp_path)
    con = sqlite3.connect(path)
    con.execute(
        "INSERT INTO address VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("a2","11711","Cascade Circle",None,"Bruce Township","MI","48065","US",42.85,-83.02),
    )
    con.commit()
    con.close()

    geocoder = SqliteGeocoder(path)
    try:
        results = geocoder.geocode("11711 Cascade Cir")
    finally:
        geocoder.close()

    assert results
    assert results[0].source == "address"
    assert results[0].display_name.startswith("11711 Cascade Circle")


def test_comma_less_numbered_address_can_match_street_prefix(tmp_path):
    path = _db(tmp_path)
    con = sqlite3.connect(path)
    con.execute(
        "INSERT INTO address VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("a3","11711","Cascade Circle",None,"Bruce Township","MI","48065","US",42.85,-83.02),
    )
    con.commit()
    con.close()

    geocoder = SqliteGeocoder(path)
    try:
        results = geocoder.geocode("11711 Cascade Cir Bruce Township MI 48065")
    finally:
        geocoder.close()

    assert results
    assert results[0].display_name.startswith("11711 Cascade Circle")


def test_numbered_address_falls_back_to_normalized_street(tmp_path):
    path = _db(tmp_path)
    con = sqlite3.connect(path)
    con.execute(
        "INSERT INTO street VALUES (?,?,?,?,?,?,?)",
        ("s2","Cascade Circle",None,None,None,42.817744,-83.017602),
    )
    con.commit()
    con.close()

    geocoder = SqliteGeocoder(path)
    try:
        results = geocoder.geocode("11711 Cascade Cir")
    finally:
        geocoder.close()

    assert results
    assert results[0].source == "street"
    assert results[0].display_name == "Cascade Circle"
    assert results[0].confidence == 0.55


def test_postcode_only_context_ranks_nearest_street_candidate(tmp_path):
    path = _db(tmp_path)
    con = sqlite3.connect(path)
    con.execute(
        "INSERT INTO address VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("zip-anchor","1","Some Road",None,None,"MI","48065","US",42.82,-83.01),
    )
    con.execute(
        "INSERT INTO street VALUES (?,?,?,?,?,?,?)",
        ("near","Cascade Circle",None,None,None,42.817744,-83.017602),
    )
    con.execute(
        "INSERT INTO street VALUES (?,?,?,?,?,?,?)",
        ("far","Cascade Circle",None,None,None,42.6292172,-83.1442853),
    )
    con.commit()
    con.close()

    geocoder = SqliteGeocoder(path)
    try:
        results = geocoder.geocode("11711 Cascade Cir 48065")
    finally:
        geocoder.close()

    assert results
    assert results[0].display_name == "Cascade Circle"
    assert math.isclose(math.degrees(results[0].position.latitude_rad), 42.817744)


def test_directional_street_with_postcode_falls_back_to_nearest_segment(tmp_path):
    path = _db(tmp_path)
    con = sqlite3.connect(path)
    con.execute(
        "INSERT INTO address VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("zip48397","1","Some Arsenal Road",None,None,"MI","48397","US",42.49,-83.04),
    )
    con.execute(
        "INSERT INTO street VALUES (?,?,?,?,?,?,?)",
        ("east11-near","East 11 Mile Road",None,None,None,42.4916,-83.0443),
    )
    con.execute(
        "INSERT INTO street VALUES (?,?,?,?,?,?,?)",
        ("east11-far","East 11 Mile Road",None,None,None,42.4957,-82.9026),
    )
    con.commit()
    con.close()

    geocoder = SqliteGeocoder(path)
    try:
        results = geocoder.geocode("6501 East 11 Mile Road 48397")
    finally:
        geocoder.close()

    assert results
    assert results[0].source == "street"
    assert results[0].display_name == "East 11 Mile Road"
    assert math.isclose(math.degrees(results[0].position.longitude_rad), -83.0443)


def test_directional_abbreviation_and_missing_suffix_are_normalized(tmp_path):
    path = _db(tmp_path)
    con = sqlite3.connect(path)
    con.execute(
        "INSERT INTO address VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("zip48397b","1","Some Arsenal Road",None,None,"MI","48397","US",42.49,-83.04),
    )
    con.execute(
        "INSERT INTO street VALUES (?,?,?,?,?,?,?)",
        ("east11","East 11 Mile Road",None,None,None,42.4916,-83.0443),
    )
    con.commit()
    con.close()

    geocoder = SqliteGeocoder(path)
    try:
        results = geocoder.geocode("6501 E. 11 Mile 48397")
    finally:
        geocoder.close()

    assert results
    assert results[0].display_name == "East 11 Mile Road"


def test_postcode_distance_affects_street_confidence(tmp_path):
    path = _db(tmp_path)
    con = sqlite3.connect(path)
    con.execute(
        "INSERT INTO address VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("zip48397c","1","Some Arsenal Road",None,None,"MI","48397","US",42.49,-83.04),
    )
    con.execute(
        "INSERT INTO street VALUES (?,?,?,?,?,?,?)",
        ("near-score","East 11 Mile Road",None,None,None,42.491,-83.041),
    )
    con.execute(
        "INSERT INTO street VALUES (?,?,?,?,?,?,?)",
        ("far-score","East 11 Mile Road",None,None,None,42.495,-82.92),
    )
    con.commit()
    con.close()

    geocoder = SqliteGeocoder(path)
    try:
        results = geocoder.geocode("6501 E. 11 Mile 48397", limit=5)
    finally:
        geocoder.close()

    assert len(results) >= 2
    assert results[0].confidence > results[1].confidence
