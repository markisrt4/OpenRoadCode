# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Build the renderer-independent OpenRoadCode offline search database from OSM."""
from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path


def _classification(tags: dict[str, str]) -> tuple[str, str, str] | None:
    amenity = tags.get("amenity", "").casefold()
    shop = tags.get("shop", "").casefold()
    public_transport = tags.get("public_transport", "").casefold()
    railway = tags.get("railway", "").casefold()
    highway = tags.get("highway", "").casefold()

    if amenity in {"restaurant", "fast_food", "cafe", "food_court", "ice_cream"}:
        return "food", amenity, amenity
    if amenity in {"fuel", "charging_station"}:
        return "fuel", amenity, amenity
    if shop in {"supermarket", "grocery", "convenience"}:
        return "grocery", "shop", shop
    if highway == "bus_stop":
        return "transit", "bus", "bus_stop"
    if public_transport in {"platform", "station", "stop_position"}:
        return "transit", "public_transport", public_transport
    if railway in {"station", "halt", "tram_stop", "subway_entrance"}:
        return "transit", "railway", railway
    return None


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE poi (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            brand TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            category TEXT NOT NULL,
            class TEXT,
            subclass TEXT
        );
        CREATE INDEX poi_category_lat_lon ON poi(category, latitude, longitude);
        CREATE INDEX poi_lat_lon ON poi(latitude, longitude);
        CREATE INDEX poi_name ON poi(name COLLATE NOCASE);

        CREATE TABLE address (
            id TEXT PRIMARY KEY,
            house_number TEXT,
            street TEXT,
            unit TEXT,
            city TEXT,
            state TEXT,
            postcode TEXT,
            country TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL
        );
        CREATE INDEX address_street_house ON address(street COLLATE NOCASE, house_number);
        CREATE INDEX address_city ON address(city COLLATE NOCASE);
        CREATE INDEX address_lat_lon ON address(latitude, longitude);

        CREATE TABLE street (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT,
            state TEXT,
            postcode TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL
        );
        CREATE INDEX street_name ON street(name COLLATE NOCASE);
        CREATE INDEX street_city ON street(city COLLATE NOCASE);

        CREATE TABLE place (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            kind TEXT,
            state TEXT,
            country TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL
        );
        CREATE INDEX place_name ON place(name COLLATE NOCASE);
        CREATE INDEX place_kind ON place(kind);
        """
    )


def _decode_geojsonseq_record(line: str) -> dict:
    record = line.lstrip("\x1e").strip()
    if not record:
        return {}
    return json.loads(record)


def _osm_id(tags: dict[str, str]) -> str | None:
    osm_type = tags.get("@type", tags.get("type", "osm"))
    osm_id = tags.get("@id", tags.get("id"))
    if not osm_id:
        return None
    return f"osm:{osm_type}:{osm_id}"


def _point(feature: dict) -> tuple[float, float] | None:
    geometry = feature.get("geometry") or {}
    if geometry.get("type") != "Point":
        return None
    coordinates = geometry.get("coordinates") or []
    if len(coordinates) < 2:
        return None
    return float(coordinates[1]), float(coordinates[0])


def _insert_feature(connection: sqlite3.Connection, feature: dict) -> None:
    properties = feature.get("properties") or {}
    tags = {str(key): str(value) for key, value in properties.items() if value is not None}
    position = _point(feature)
    object_id = _osm_id(tags)
    if position is None or object_id is None:
        return
    latitude, longitude = position

    name = tags.get("name", "").strip()
    classification = _classification(tags)
    if name and classification is not None:
        category, source_class, source_subclass = classification
        connection.execute(
            "INSERT OR REPLACE INTO poi "
            "(id,name,brand,latitude,longitude,category,class,subclass) VALUES (?,?,?,?,?,?,?,?)",
            (object_id, name, tags.get("brand"), latitude, longitude,
             category, source_class, source_subclass),
        )

    street_name = tags.get("addr:street", "").strip()
    house_number = tags.get("addr:housenumber", "").strip()
    if street_name and house_number:
        connection.execute(
            "INSERT OR REPLACE INTO address "
            "(id,house_number,street,unit,city,state,postcode,country,latitude,longitude) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (object_id, house_number, street_name, tags.get("addr:unit"),
             tags.get("addr:city"), tags.get("addr:state"), tags.get("addr:postcode"),
             tags.get("addr:country"), latitude, longitude),
        )

    place_kind = tags.get("place", "").casefold()
    if name and place_kind in {
        "city", "town", "village", "hamlet", "suburb", "neighbourhood", "quarter"
    }:
        connection.execute(
            "INSERT OR REPLACE INTO place "
            "(id,name,kind,state,country,latitude,longitude) VALUES (?,?,?,?,?,?,?)",
            (object_id, name, place_kind, tags.get("addr:state"), tags.get("addr:country"),
             latitude, longitude),
        )

    highway = tags.get("highway", "").casefold()
    if name and highway and highway not in {
        "bus_stop", "crossing", "traffic_signals", "stop", "give_way", "street_lamp"
    }:
        connection.execute(
            "INSERT OR REPLACE INTO street "
            "(id,name,city,state,postcode,latitude,longitude) VALUES (?,?,?,?,?,?,?)",
            (object_id, name, tags.get("addr:city"), tags.get("addr:state"),
             tags.get("addr:postcode"), latitude, longitude),
        )


def build_search_index(source_pbf: Path, destination: Path) -> dict[str, int]:
    """Extract searchable point data from ``source_pbf`` into one SQLite database."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)

    command = [
        "osmium", "export", str(source_pbf),
        "--geometry-types=point",
        "--add-unique-id=type_id",
        "--attributes=type,id",
        "-f", "geojsonseq",
        "-o", "-",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)
    assert process.stdout is not None

    connection = sqlite3.connect(destination)
    try:
        _create_schema(connection)
        for line in process.stdout:
            feature = _decode_geojsonseq_record(line)
            if feature:
                _insert_feature(connection, feature)
        connection.commit()
        counts = {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("poi", "address", "street", "place")
        }
    finally:
        process.stdout.close()
        return_code = process.wait()
        connection.close()
    if return_code != 0:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"osmium export failed with status {return_code}")
    return counts


def build_poi_index(source_pbf: Path, destination: Path) -> int:
    """Compatibility wrapper for callers that still request a POI-only index."""
    return build_search_index(source_pbf, destination)["poi"]
