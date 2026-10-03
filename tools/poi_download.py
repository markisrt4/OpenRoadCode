# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Download regional OSM POIs into the offline index without a map build."""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime
import json
import math
import os
from pathlib import Path
import sqlite3
import tempfile
import urllib.parse
import urllib.request

from common.navigation_data import search_database_path
from tools.map_builder.builder.poi_index import _create_schema, _insert_point_feature
from tools.map_builder.builder.validate import validate_search_index

ENDPOINT = 'https://overpass-api.de/api/interpreter'


def default_database() -> Path:
    return search_database_path()

def build_query(latitude: float, longitude: float, radius_km: float) -> str:
    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise ValueError('latitude must be between -90 and 90')
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise ValueError('longitude must be between -180 and 180')
    if not math.isfinite(radius_km) or not 0 < radius_km <= 25:
        raise ValueError('radius must be greater than zero and at most 25 km')
    area = f'(around:{radius_km * 1000:g},{latitude:.7f},{longitude:.7f})'
    filters = [
        '["amenity"~"^(restaurant|fast_food|cafe|food_court|ice_cream|fuel|charging_station)$"]',
        '["shop"~"^(supermarket|grocery|convenience)$"]',
        '["highway"="bus_stop"]',
        '["public_transport"~"^(platform|station|stop_position)$"]',
        '["railway"~"^(station|halt|tram_stop|subway_entrance)$"]',
    ]
    return '[out:json][timeout:25];(' + ''.join(
        f'nwr{selector}{area};' for selector in filters
    ) + ');out center tags;'


def download(query: str, endpoint: str = ENDPOINT) -> dict:
    request = urllib.request.Request(
        endpoint, data=urllib.parse.urlencode({'data': query}).encode(),
        headers={'User-Agent': 'OpenRoadCode-POI/1.0',
                 'Content-Type': 'application/x-www-form-urlencoded'},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        body = response.read(32 * 1024 * 1024 + 1)
    if len(body) > 32 * 1024 * 1024:
        raise ValueError('Response too large; use a smaller radius')
    return json.loads(body)


def _within_area(lat: float, lon: float, area: tuple[float, float, float]) -> bool:
    center_lat, center_lon, radius_km = area
    delta_lat = math.radians(lat - center_lat)
    delta_lon = math.radians(lon - center_lon)
    haversine = (math.sin(delta_lat / 2) ** 2
                 + math.cos(math.radians(lat)) * math.cos(math.radians(center_lat))
                 * math.sin(delta_lon / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(min(1, max(0, haversine)))) <= radius_km


def install(payload: dict, destination: Path, *,
            refresh_area: tuple[float, float, float] | None = None) -> dict[str, int]:
    """Replace scoped OSM POIs in a staged copy; unscoped imports only merge."""
    if not isinstance(payload, dict) or not isinstance(payload.get('elements'), list):
        raise ValueError('Expected an Overpass JSON response with elements')
    if payload.get('remark'):
        raise ValueError(f"Overpass reported an incomplete query: {payload['remark']}")
    if refresh_area is not None:
        build_query(*refresh_area)  # Validate the same area used for downloading.
        metadata = payload.get('osm3s')
        timestamp = metadata.get('timestamp_osm_base') if isinstance(metadata, dict) else None
        if payload.get('version') != 0.6 or not isinstance(timestamp, str):
            raise ValueError('Area refresh requires a complete Overpass snapshot with OSM timestamp')
        parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        if parsed_timestamp.tzinfo is None:
            raise ValueError('Overpass snapshot timestamp must include a timezone')
    destination = destination.expanduser().absolute()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.poi-download-', suffix='.sqlite', dir=destination.parent)
    os.close(fd)
    staged = Path(name)
    try:
        with closing(sqlite3.connect(staged)) as db, db:
            if destination.exists():
                validate_search_index(destination)
                with closing(sqlite3.connect(f'{destination.as_uri()}?mode=ro', uri=True)) as old:
                    old.backup(db)
            else:
                _create_schema(db)
            if 'website' not in {row[1] for row in db.execute('PRAGMA table_info(poi)')}:
                db.execute('ALTER TABLE poi ADD COLUMN website TEXT')
            if refresh_area is not None:
                # All supported categories were requested. Remove old OSM records
                # inside that circle, including places deleted or reclassified in
                # OSM. Reinsert the current snapshot below in this staged database.
                center_lat, _, radius_km = refresh_area
                latitude_delta = math.degrees(radius_km / 6371)
                candidates = db.execute(
                    "SELECT id,latitude,longitude FROM poi WHERE id GLOB 'osm:*' "
                    "AND category IN ('food','fuel','grocery','transit') "
                    "AND latitude BETWEEN ? AND ?",
                    (center_lat - latitude_delta, center_lat + latitude_delta),
                ).fetchall()
                stale = [(identifier,) for identifier, lat, lon in candidates
                         if _within_area(lat, lon, refresh_area)]
                db.executemany('DELETE FROM poi WHERE id = ?', stale)
            for element in payload['elements']:
                if not isinstance(element, dict):
                    raise ValueError('Malformed OSM element')
                kind = element.get('type')
                object_id = element.get('id')
                tags = element.get('tags', {})
                position = element if kind == 'node' else element.get('center', {})
                if kind not in {'node', 'way', 'relation'} or not isinstance(object_id, int):
                    raise ValueError('OSM element has invalid type or id')
                if not isinstance(tags, dict) or not isinstance(position, dict):
                    raise ValueError('OSM element has invalid tags or coordinates')
                lat, lon = position.get('lat'), position.get('lon')
                if lat is None or lon is None:
                    if refresh_area is not None:
                        raise ValueError('Incomplete OSM geometry; area refresh canceled')
                    continue
                if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                    raise ValueError('OSM coordinates must be numeric')
                if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                    raise ValueError('OSM coordinates out of range')
                _insert_point_feature(db, {
                    'type': 'Feature',
                    'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
                    'properties': {**tags, '@type': kind, '@id': object_id},
                })
            db.commit()
            counts = dict(db.execute('SELECT category, count(*) FROM poi GROUP BY category'))
        validate_search_index(staged)
        staged.replace(destination)
        return counts
    finally:
        staged.unlink(missing_ok=True)


def cached_position() -> tuple[float, float]:
    from controllers.cache import PersistentCache
    from controllers.navigation.position_snapshot_cache import (
        DEFAULT_POSITION_CACHE_DIRECTORY, PositionSnapshotCache,
    )
    state = PositionSnapshotCache(PersistentCache(DEFAULT_POSITION_CACHE_DIRECTORY)).load()
    if state is None or not state.has_fix or state.latitude_deg is None or state.longitude_deg is None:
        raise ValueError('No cached navigation fix; use --bridge-position or supply --lat and --lon')
    return state.latitude_deg, state.longitude_deg


def bridge_position() -> tuple[float, float]:
    from hardware_io.android.sensor_bridge_client import AndroidSensorBridgeClient
    try:
        sample = AndroidSensorBridgeClient(timeout_seconds=3).read_location()
    except RuntimeError as exc:
        raise ValueError(
            'Phone location unavailable. Open Bridge, enable Android Sensors under '
            f'Navigation, and grant precise location permission. Details: {exc}'
        ) from exc
    if 'simulat' in sample.provider.casefold():
        raise ValueError('Bridge is using simulated location; select Android Sensors')
    if sample.age_ms < 0 or sample.age_ms > 120_000:
        raise ValueError('Bridge location is older than two minutes; wait for a fresh fix')
    return sample.latitude_deg, sample.longitude_deg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lat', type=float)
    parser.add_argument('--lon', type=float)
    parser.add_argument('--bridge-position', action='store_true',
                        help='Read current phone location from Android Bridge, without an ORC cache')
    parser.add_argument('--radius-km', type=float, default=10)
    parser.add_argument('--database', type=Path, default=default_database())
    parser.add_argument('--endpoint', default=ENDPOINT)
    parser.add_argument('--input-json', type=Path, help='Import a previously downloaded Overpass response')
    args = parser.parse_args(argv)
    try:
        refresh_area = None
        if args.input_json:
            payload = json.loads(args.input_json.read_text())
            if args.bridge_position:
                raise ValueError('Saved JSON requires explicit --lat/--lon for area refresh')
            if (args.lat is None) != (args.lon is None):
                raise ValueError('Supply --lat and --lon together')
            if args.lat is not None:
                refresh_area = (args.lat, args.lon, args.radius_km)
        else:
            if (args.lat is None) != (args.lon is None):
                raise ValueError('Supply --lat and --lon together')
            if args.bridge_position and args.lat is not None:
                raise ValueError('Use either --bridge-position or --lat/--lon')
            if args.bridge_position:
                lat, lon = bridge_position()
            else:
                lat, lon = cached_position() if args.lat is None else (args.lat, args.lon)
            query = build_query(lat, lon, args.radius_km)
            print(f'Downloading OSM POIs within {args.radius_km:g} km of {lat:.6f},{lon:.6f}', flush=True)
            payload = download(query, args.endpoint)
            refresh_area = (lat, lon, args.radius_km)
        counts = install(payload, args.database.absolute(), refresh_area=refresh_area)
        print(f'Installed: {args.database}')
        print('Index totals: ' + ', '.join(f'{key}={value}' for key, value in sorted(counts.items())))
        print('Restart ORC to reopen the index. Data: © OpenStreetMap contributors (ODbL).')
        return 0
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f'POI download failed: {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
