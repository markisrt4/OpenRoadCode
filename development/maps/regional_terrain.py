"""Build a resumable multi-resolution USGS 3DEP terrain pack for Metro Detroit."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from apps.launchers.local_terrain_pack import load_terrain
from development.maps.install_region import COVERAGES
from tools.map_builder.builder.terrain import download_bounds
from tools.map_builder.builder.map_3d import PRESETS


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


def _lod_tiles(bounds):
    yield "overview", bounds, 33, 0, 0
    for tile_id, tile_bounds in terrain_tiles(bounds, 2):
        yield "regional-" + tile_id, tile_bounds, 65, 1, 9
    for preset in ("detroit-midtown", "rochester", "southfield", "pine-knob"):
        yield "focus-" + preset, PRESETS[preset][1], 129, 2, 12


def build(destination: Path, *, coverage: str = "metro-detroit", size: int | None = None) -> None:
    title, bounds = COVERAGES[coverage]
    destination = Path(destination)
    if destination.exists():
        load_terrain(destination)
        return
    cache = destination.with_name(destination.name + ".download")
    cache.mkdir(parents=True, exist_ok=True)
    records = []
    definitions = list(_lod_tiles(bounds)) if size is None else [
        (tile_id, tile_bounds, size, 0, 0) for tile_id, tile_bounds in terrain_tiles(bounds)
    ]
    for index, (tile_id, tile_bounds, grid_size, detail_level, minimum_zoom) in enumerate(definitions, 1):
        tile = cache / tile_id
        print(f"Terrain tile {index}/{len(definitions)}: {tile_id} (LOD {detail_level})", flush=True)
        download_bounds(tile, f"{title} {tile_id}", tile_bounds, size=grid_size)
        records.append({
            "id": tile_id,
            "path": tile_id,
            "bounds_deg": tile_bounds,
            "sha256": hashlib.sha256((tile / "terrain.json").read_bytes()).hexdigest(),
            "detail_level": detail_level,
            "minimum_zoom": minimum_zoom,
        })
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
            "lod": "overview 33×33; regional 2×2 at 65×65; focus areas at 129×129",
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }
        (prepared / "manifest.json").write_text(json.dumps(manifest, indent=2))
        load_terrain(prepared)
        prepared.rename(destination)
    shutil.rmtree(cache)
