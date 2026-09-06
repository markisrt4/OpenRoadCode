# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Build the renderer-independent OpenRoadCode offline search database from OSM."""
from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path


def _classification(tags: dict[str, str]) -> tuple[str, str, str] | None:
    amenity = tags.get("amenity", "").casefold(); shop = tags.get("shop", "").casefold()
    public_transport = tags.get("public_transport", "").casefold(); railway = tags.get("railway", "").casefold(); highway = tags.get("highway", "").casefold()
    if amenity in {"restaurant", "fast_food", "cafe", "food_court", "ice_cream"}: return "food", amenity, amenity
    if amenity in {"fuel", "charging_station"}: return "fuel", amenity, amenity
    if shop in {"supermarket", "grocery", "convenience"}: return "grocery", "shop", shop
    if highway == "bus_stop": return "transit", "bus", "bus_stop"
    if public_transport in {"platform", "station", "stop_position"}: return "transit", "public_transport", public_transport
    if railway in {"station", "halt", "tram_stop", "subway_entrance"}: return "transit", "railway", railway
    return None


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE poi (id TEXT PRIMARY KEY,name TEXT NOT NULL,brand TEXT,latitude REAL NOT NULL,longitude REAL NOT NULL,category TEXT NOT NULL,class TEXT,subclass TEXT);
        CREATE INDEX poi_category_lat_lon ON poi(category,latitude,longitude); CREATE INDEX poi_lat_lon ON poi(latitude,longitude); CREATE INDEX poi_name ON poi(name COLLATE NOCASE);
        CREATE TABLE address (id TEXT PRIMARY KEY,house_number TEXT,street TEXT,unit TEXT,city TEXT,state TEXT,postcode TEXT,country TEXT,latitude REAL NOT NULL,longitude REAL NOT NULL);
        CREATE INDEX address_street_house ON address(street COLLATE NOCASE,house_number); CREATE INDEX address_city ON address(city COLLATE NOCASE); CREATE INDEX address_lat_lon ON address(latitude,longitude);
        CREATE TABLE street (id TEXT PRIMARY KEY,name TEXT NOT NULL,city TEXT,state TEXT,postcode TEXT,latitude REAL NOT NULL,longitude REAL NOT NULL);
        CREATE INDEX street_name ON street(name COLLATE NOCASE); CREATE INDEX street_city ON street(city COLLATE NOCASE);
        CREATE TABLE place (id TEXT PRIMARY KEY,name TEXT NOT NULL,kind TEXT,state TEXT,country TEXT,latitude REAL NOT NULL,longitude REAL NOT NULL);
        CREATE INDEX place_name ON place(name COLLATE NOCASE); CREATE INDEX place_kind ON place(kind);
    """)


def _decode_geojsonseq_record(line: str) -> dict:
    record=line.lstrip("\x1e").strip(); return json.loads(record) if record else {}

def _tags(feature:dict)->dict[str,str]:
    return {str(k):str(v) for k,v in (feature.get("properties") or {}).items() if v is not None}

def _osm_id(tags:dict[str,str])->str|None:
    osm_id=tags.get("@id",tags.get("id")); return f"osm:{tags.get('@type',tags.get('type','osm'))}:{osm_id}" if osm_id else None

def _representative_point(feature:dict)->tuple[float,float]|None:
    geometry=feature.get("geometry") or {}; kind=geometry.get("type"); coordinates=geometry.get("coordinates") or []
    if kind=="Point" and len(coordinates)>=2: return float(coordinates[1]),float(coordinates[0])
    if kind=="LineString" and coordinates:
        # The middle vertex is stable, cheap, and guaranteed to lie on the way.
        point=coordinates[len(coordinates)//2]
        if len(point)>=2:return float(point[1]),float(point[0])
    return None

def _insert_point_feature(connection:sqlite3.Connection,feature:dict)->None:
    tags=_tags(feature); position=_representative_point(feature); object_id=_osm_id(tags)
    if position is None or object_id is None:return
    latitude,longitude=position; name=tags.get("name","").strip(); classification=_classification(tags)
    if name and classification is not None:
        category,source_class,source_subclass=classification
        connection.execute("INSERT OR REPLACE INTO poi (id,name,brand,latitude,longitude,category,class,subclass) VALUES (?,?,?,?,?,?,?,?)",(object_id,name,tags.get("brand"),latitude,longitude,category,source_class,source_subclass))
    street_name=tags.get("addr:street","").strip(); house_number=tags.get("addr:housenumber","").strip()
    if street_name and house_number:
        connection.execute("INSERT OR REPLACE INTO address (id,house_number,street,unit,city,state,postcode,country,latitude,longitude) VALUES (?,?,?,?,?,?,?,?,?,?)",(object_id,house_number,street_name,tags.get("addr:unit"),tags.get("addr:city"),tags.get("addr:state"),tags.get("addr:postcode"),tags.get("addr:country"),latitude,longitude))
    place_kind=tags.get("place","").casefold()
    if name and place_kind in {"city","town","village","hamlet","suburb","neighbourhood","quarter"}:
        connection.execute("INSERT OR REPLACE INTO place (id,name,kind,state,country,latitude,longitude) VALUES (?,?,?,?,?,?,?)",(object_id,name,place_kind,tags.get("addr:state"),tags.get("addr:country"),latitude,longitude))

def _insert_street_feature(connection:sqlite3.Connection,feature:dict)->None:
    tags=_tags(feature); name=tags.get("name","").strip(); highway=tags.get("highway","").casefold(); object_id=_osm_id(tags); position=_representative_point(feature)
    if not name or not highway or object_id is None or position is None:return
    if highway in {"bus_stop","crossing","traffic_signals","stop","give_way","street_lamp"}:return
    latitude,longitude=position
    connection.execute("INSERT OR REPLACE INTO street (id,name,city,state,postcode,latitude,longitude) VALUES (?,?,?,?,?,?,?)",(object_id,name,tags.get("addr:city"),tags.get("addr:state"),tags.get("addr:postcode"),latitude,longitude))

def _export(source_pbf:Path,geometry_types:str):
    command=["osmium","export",str(source_pbf),f"--geometry-types={geometry_types}","--add-unique-id=type_id","--attributes=type,id","-f","geojsonseq","-o","-"]
    process=subprocess.Popen(command,stdout=subprocess.PIPE,text=True); assert process.stdout is not None
    return process

def _consume(process,connection,insert)->None:
    try:
        for line in process.stdout:
            feature=_decode_geojsonseq_record(line)
            if feature:insert(connection,feature)
    finally:
        process.stdout.close(); return_code=process.wait()
    if return_code!=0:raise RuntimeError(f"osmium export failed with status {return_code}")

def build_search_index(source_pbf:Path,destination:Path)->dict[str,int]:
    """Build POI, address, street, and place indexes from one OSM extract."""
    destination.parent.mkdir(parents=True,exist_ok=True); destination.unlink(missing_ok=True); connection=sqlite3.connect(destination)
    try:
        _create_schema(connection)
        _consume(_export(source_pbf,"point"),connection,_insert_point_feature)
        _consume(_export(source_pbf,"linestring"),connection,_insert_street_feature)
        connection.commit()
        counts={table:int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in ("poi","address","street","place")}
    except Exception:
        connection.close(); destination.unlink(missing_ok=True); raise
    connection.close(); return counts

def build_poi_index(source_pbf:Path,destination:Path)->int:
    """Compatibility wrapper for callers that still request a POI-only index."""
    return build_search_index(source_pbf,destination)["poi"]
