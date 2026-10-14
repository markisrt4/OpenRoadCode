"""Build a resumable 4×4 USGS 3DEP terrain mosaic for Metro Detroit."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from apps.launchers.local_terrain_pack import load_terrain
from development.maps.install_region import COVERAGES
from tools.map_builder.builder.terrain import download_bounds


def terrain_tiles(bounds):
    west, south, east, north = bounds
    for row in range(4):
        for column in range(4):
            yield (
                f"r{row}-c{column}",
                (
                    west + (east-west)*column/4,
                    south + (north-south)*row/4,
                    west + (east-west)*(column+1)/4,
                    south + (north-south)*(row+1)/4,
                ),
            )


def build(destination: Path, *, coverage: str = "metro-detroit", size: int = 65) -> None:
    title, bounds = COVERAGES[coverage]
    destination = Path(destination)
    if destination.exists():
        load_terrain(destination)
        return
    cache = destination.with_name(destination.name + ".download")
    cache.mkdir(parents=True, exist_ok=True)
    records = []
    for index, (tile_id, tile_bounds) in enumerate(terrain_tiles(bounds), 1):
        tile = cache / tile_id
        print(f"Terrain tile {index}/16: {tile_id}", flush=True)
        download_bounds(tile, f"{title} {tile_id}", tile_bounds, size=size)
        records.append({
            "id": tile_id,
            "path": tile_id,
            "bounds_deg": tile_bounds,
            "sha256": hashlib.sha256((tile / "terrain.json").read_bytes()).hexdigest(),
        })
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent, prefix=".terrain-mosaic-") as temporary:
        prepared = Path(temporary) / "pack"
        prepared.mkdir()
        for record in records:
            shutil.copytree(cache / record["id"], prepared / record["path"])
        manifest = {
            "schema": 2,
            "layers": ["terrain"],
            "title": title + " tiled 3DEP terrain",
            "attribution": "USGS 3DEP · The National Map",
            "bounds_deg": bounds,
            "tiles": records,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }
        (prepared / "manifest.json").write_text(json.dumps(manifest, indent=2))
        load_terrain(prepared)
        prepared.rename(destination)
    shutil.rmtree(cache)
