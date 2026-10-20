"""Read a bounded local terrain pack without introducing renderer dependencies."""

import hashlib
import json
import math
from pathlib import Path

from common.xdg_paths import openroadcode_data_dir
from common.navigation_data import navigation_data_root
from ui.navigation.local_imagery_state import LocalImageryState
from ui.navigation.local_terrain_state import LocalTerrainMosaicState, LocalTerrainState


def detroit_terrain_directory():
    return openroadcode_data_dir("map-packs", "detroit-terrain-v1")


def midtown_terrain_directory():
    """Device-owned downloads survive shared navigation dataset updates."""
    return openroadcode_data_dir("map-packs", "detroit-midtown-terrain-v1")


def pine_knob_terrain_directory():
    return openroadcode_data_dir("map-packs", "pine-knob-terrain-v1")


def metro_detroit_terrain_directory():
    return openroadcode_data_dir("map-packs", "metro-detroit-terrain-active")


def regional_terrain_directory(coverage):
    return openroadcode_data_dir("map-packs", coverage + "-terrain-active")


def preferred_terrain_directory(destination=None):
    packs = navigation_data_root()/'maps/3d/packs'
    from development.maps.terrain_regions import MICHIGAN_SHARDS
    candidates = (openroadcode_data_dir('map-packs','metro-detroit-terrain-active'),
                  *(regional_terrain_directory(name) for name in MICHIGAN_SHARDS),
                  regional_terrain_directory('michigan-overview'),
                  packs/'detroit-midtown-terrain', midtown_terrain_directory(),
                  packs/'detroit-downtown-terrain', detroit_terrain_directory(),
                  packs/'pine-knob-terrain', pine_knob_terrain_directory(),
                  packs/'rochester-terrain',openroadcode_data_dir('map-packs','rochester-terrain-v1'),
                  packs/'southfield-terrain',openroadcode_data_dir('map-packs','southfield-terrain-v1'))
    if destination is not None:
        longitude = math.degrees(destination.longitude_rad)
        latitude = math.degrees(destination.latitude_rad)
        for directory in candidates:
            if (directory/'manifest.json').is_file():
                manifest = json.loads((directory/'manifest.json').read_text())
                west, south, east, north = manifest['bounds_deg']
                if west <= longitude <= east and south <= latitude <= north:
                    return directory
    for directory in candidates:
        if (directory/'manifest.json').is_file():
            return directory
    return detroit_terrain_directory()


def load_terrain(directory):
    root = Path(directory).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    schema = manifest.get("schema")
    if schema in (2, 3) and manifest.get("layers") == ["terrain"]:
        records = manifest.get("tiles")
        if not isinstance(records, list) or not 1 <= len(records) <= 64:
            raise ValueError("Terrain mosaic requires 1–64 tiles")
        names = set()
        tiles = []
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("path"), str):
                raise ValueError("Invalid terrain mosaic tile")
            relative = Path(record["path"])
            tile_root = (root / relative).resolve()
            if (relative.is_absolute() or ".." in relative.parts or tile_root == root
                    or not tile_root.is_relative_to(root) or record["path"] in names):
                raise ValueError("Terrain tile must be a unique directory inside the pack")
            names.add(record["path"])
            detail_level = record.get("detail_level", 0)
            minimum_zoom = record.get("minimum_zoom", 0)
            if (type(detail_level) is not int or not 0 <= detail_level <= 8
                    or type(minimum_zoom) is not int or not 0 <= minimum_zoom <= 18
                    or (schema == 2 and (detail_level or minimum_zoom))):
                raise ValueError("Invalid terrain tile detail metadata")
            state = _load_single_terrain(tile_root, detail_level=detail_level,
                                         minimum_zoom=minimum_zoom)
            expected_bounds = record.get("bounds_deg")
            actual_bounds = [math.degrees(value) for value in (
                state.coverage.west_rad, state.coverage.south_rad,
                state.coverage.east_rad, state.coverage.north_rad)]
            if (not isinstance(expected_bounds, list) or len(expected_bounds) != 4
                    or any(abs(float(a)-b) > 1e-9 for a, b in zip(expected_bounds, actual_bounds))):
                raise ValueError("Terrain mosaic tile bounds do not match its manifest")
            digest = hashlib.sha256((tile_root / "terrain.json").read_bytes()).hexdigest()
            if record.get("sha256") != digest:
                raise ValueError("Terrain mosaic tile checksum does not match")
            tiles.append(state)
        tiles = tuple(tiles)
        maximum_zoom = manifest.get("maximum_zoom", 13)
        return LocalTerrainMosaicState(tiles, str(manifest.get("attribution", "")), maximum_zoom)
    if manifest.get("schema") != 1:
        raise ValueError("Unsupported terrain schema")
    return _load_single_terrain(root)


def _load_single_terrain(root, *, detail_level=0, minimum_zoom=0):
    root = Path(root).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("schema") != 1:
        raise ValueError("Terrain mosaic children must use schema 1")
    payload = (root / "terrain.json").resolve()
    if not payload.is_relative_to(root):
        raise ValueError("Terrain data must remain inside the pack")
    if payload.stat().st_size > 2*1024*1024:
        raise ValueError("Prototype terrain exceeds 2 MB")
    content = payload.read_bytes()
    if hashlib.sha256(content).hexdigest() != manifest["sha256"]:
        raise ValueError("Terrain checksum does not match manifest")
    data = json.loads(content)
    coverage = LocalImageryState(manifest["title"], manifest["attribution"],
                                 *(math.radians(v) for v in manifest["bounds_deg"]))
    return LocalTerrainState(coverage, data["width"], data["height"], tuple(data["heights_m"]),
                              data["reference_height_m"], data["vertical_datum"],
                              detail_level, minimum_zoom)
