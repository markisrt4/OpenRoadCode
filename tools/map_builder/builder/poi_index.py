# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Build the renderer-independent OpenRoadCode POI search index from OSM."""
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
        CREATE INDEX poi_category_lat_lon
            ON poi(category, latitude, longitude);
        CREATE INDEX poi_lat_lon
            ON poi(latitude, longitude);
        """
    )


def build_poi_index(source_pbf: Path, destination: Path) -> int:
    """Extract searchable named POIs from ``source_pbf`` into SQLite."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)

    # GeoJSONSeq keeps memory bounded even for multi-state extracts. This first
    # pass intentionally indexes point features; area-derived POIs are handled
    # separately rather than pretending osmium turns polygons into centroids.
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
            feature = json.loads(line)
            properties = feature.get("properties") or {}
            tags = {
                str(key): str(value)
                for key, value in properties.items()
                if value is not None
            }
            name = tags.get("name", "").strip()
            if not name:
                continue
            classification = _classification(tags)
            if classification is None:
                continue
            geometry = feature.get("geometry") or {}
            if geometry.get("type") != "Point":
                continue
            coordinates = geometry.get("coordinates") or []
            if len(coordinates) < 2:
                continue
            longitude, latitude = float(coordinates[0]), float(coordinates[1])
            category, source_class, source_subclass = classification
            osm_type = tags.get("@type", tags.get("type", "osm"))
            osm_id = tags.get("@id", tags.get("id"))
            if not osm_id:
                continue
            poi_id = f"osm:{osm_type}:{osm_id}"
            connection.execute(
                "INSERT OR REPLACE INTO poi "
                "(id,name,brand,latitude,longitude,category,class,subclass) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    poi_id,
                    name,
                    tags.get("brand"),
                    latitude,
                    longitude,
                    category,
                    source_class,
                    source_subclass,
                ),
            )
        connection.commit()
        count = int(connection.execute("SELECT COUNT(*) FROM poi").fetchone()[0])
    finally:
        process.stdout.close()
        return_code = process.wait()
        connection.close()
    if return_code != 0:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"osmium export failed with status {return_code}")
    return count
