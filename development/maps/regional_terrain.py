"""Build a resumable multi-resolution USGS 3DEP terrain pack for Metro Detroit."""

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from apps.launchers.local_terrain_pack import load_terrain
from development.maps.install_region import COVERAGES
from tools.map_builder.builder.terrain import download_bounds
from tools.map_builder.builder.map_3d import PRESETS
from development.maps.terrain_regions import MICHIGAN_COVERAGES


def terrain_tiles(bounds, divisions=4):
    west, south, east, north = bounds
    for row in range(divisions):
        for column in range(divisions):
            yield (
                f"r{row}-c{column}",
                (
                    west + (east-west)*column/divisions,
                    south + (north-south)*row/divisions,
                    west + (east-west)*(column+1)/divisions,
                    south + (north-south)*(row+1)/divisions,
                ),
            )


def _metro_lod_tiles(bounds):
    yield "overview", bounds, 33, 0, 0
    for tile_id, tile_bounds in terrain_tiles(bounds, 4):
        yield "regional-" + tile_id, tile_bounds, 129, 1, 9
    for preset in ("detroit-midtown", "rochester", "southfield", "pine-knob"):
        yield "focus-" + preset, PRESETS[preset][1], 129, 2, 12


def _definitions(coverage, bounds, size=None):
    if size is not None:
        return [(tile_id, tile_bounds, size, 0, 0)
                for tile_id, tile_bounds in terrain_tiles(bounds)]
    if coverage == "metro-detroit":
        return list(_metro_lod_tiles(bounds))
    return [(tile_id, tile_bounds, 129, 0, 0)
            for tile_id, tile_bounds in terrain_tiles(bounds, 8)]


def _build_tile(cache, title, index, total, definition):
    tile_id, tile_bounds, grid_size, detail_level, minimum_zoom = definition
    tile = cache / tile_id
    print(f"Terrain tile {index}/{total}: {tile_id} (LOD {detail_level})", flush=True)
    download_bounds(tile, f"{title} {tile_id}", tile_bounds, size=grid_size)
    return {
        "id": tile_id,
        "path": tile_id,
        "bounds_deg": tile_bounds,
        "sha256": hashlib.sha256((tile / "terrain.json").read_bytes()).hexdigest(),
        "detail_level": detail_level,
        "minimum_zoom": minimum_zoom,
    }


def build_michigan_row(cache: Path, *, coverage: str, row: int) -> None:
    """Build and validate one row of a Michigan pack's shared tile cache."""
    if coverage not in MICHIGAN_COVERAGES:
        raise ValueError(f"Not a Michigan terrain coverage: {coverage}")
    if row not in range(8):
        raise ValueError(f"Michigan terrain row must be 0-7, got {row}")
    title, bounds = MICHIGAN_COVERAGES[coverage]
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    definitions = _definitions(coverage, bounds)
    selected = [(index, definition) for index, definition in enumerate(definitions, 1)
                if definition[0].startswith(f"r{row}-")]
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(
            lambda item: _build_tile(cache, title, item[0], len(definitions), item[1]),
            selected,
        ))


def build(destination: Path, *, coverage: str = "metro-detroit", size: int | None = None) -> None:
    title, bounds = (COVERAGES[coverage] if coverage == "metro-detroit"
                     else MICHIGAN_COVERAGES[coverage])
    destination = Path(destination)
    if destination.exists():
        load_terrain(destination)
        return
    cache = destination.with_name(destination.name + ".download")
    cache.mkdir(parents=True, exist_ok=True)
    definitions = _definitions(coverage, bounds, size)
    def build_tile(item):
        return _build_tile(cache, title, item[0], len(definitions), item[1])
    indexed = list(enumerate(definitions, 1))
    if coverage in MICHIGAN_COVERAGES:
        # Statewide grids generate many USGS sampling calls. Two concurrent
        # tiles are intentionally gentler on the public service and more stable
        # than the four-way prototype used for local builds.
        with ThreadPoolExecutor(max_workers=2) as executor:
            records = list(executor.map(build_tile, indexed))
    else:
        records = [build_tile(item) for item in indexed]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent, prefix=".terrain-mosaic-") as temporary:
        prepared = Path(temporary) / "pack"
        prepared.mkdir()
        for record in records:
            shutil.copytree(cache / record["id"], prepared / record["path"])
        manifest = {
            "schema": 3,
            "layers": ["terrain"],
            "title": title + " tiled 3DEP terrain",
            "attribution": "USGS 3DEP · The National Map",
            "bounds_deg": bounds,
            "tiles": records,
            "maximum_zoom": 16,
            "lod": ("overview 33×33; regional 4×4 and focus areas at 129×129"
                    if coverage == "metro-detroit" else
                    "8×8 regional tiles at 129×129"),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }
        (prepared / "manifest.json").write_text(json.dumps(manifest, indent=2))
        load_terrain(prepared)
        prepared.rename(destination)
    shutil.rmtree(cache)
