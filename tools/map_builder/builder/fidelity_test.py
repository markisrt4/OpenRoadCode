# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Build small MBTiles samples for zoom-level fidelity comparisons."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .build import (
    SCRATCH_ROOT,
    TILEMAKER_CONFIG,
    TILEMAKER_PROCESS,
    _download_and_verify,
    run,
)
from .geofabrik import fetch_index, resolve_region_ids

INDEX_PATH = Path("/cache/geofabrik-index-v1-nogeom.json")


def _parse_bbox(value: str) -> tuple[float, float, float, float]:
    try:
        west, south, east, north = (float(part.strip()) for part in value.split(","))
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("bbox must be WEST,SOUTH,EAST,NORTH") from exc
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise argparse.ArgumentTypeError("invalid bbox")
    return west, south, east, north


def _write_zoom_config(source: Path, destination: Path, max_zoom: int) -> None:
    config = json.loads(source.read_text(encoding="utf-8"))
    settings = config["settings"]
    old_max = int(settings["maxzoom"])
    settings["maxzoom"] = max_zoom
    settings["basezoom"] = max_zoom
    if "combine_below" in settings and int(settings["combine_below"]) == old_max:
        settings["combine_below"] = max_zoom

    for layer in config.get("layers", {}).values():
        if isinstance(layer, dict) and int(layer.get("maxzoom", -1)) == old_max:
            layer["maxzoom"] = max_zoom

    destination.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def build_samples(region_id: str, bbox: tuple[float, float, float, float], zooms: list[int]) -> Path:
    regions = fetch_index(INDEX_PATH)
    region = resolve_region_ids(regions, [region_id])[0]
    source = _download_and_verify(region)

    root = SCRATCH_ROOT / "fidelity-test"
    root.mkdir(parents=True, exist_ok=True)
    clipped = root / "sample.osm.pbf"
    clipped.unlink(missing_ok=True)
    bbox_text = ",".join(str(value) for value in bbox)
    run([
        "osmium", "extract",
        "--overwrite",
        "--strategy", "smart",
        "--bbox", bbox_text,
        "-o", str(clipped),
        str(source),
    ])
    run(["osmium", "fileinfo", "-e", str(clipped)])

    for zoom in zooms:
        config = root / f"config-z{zoom}.json"
        output = root / f"sample-z{zoom}.mbtiles"
        store = root / f"tilemaker-store-z{zoom}"
        output.unlink(missing_ok=True)
        if store.exists():
            shutil.rmtree(store)
        store.mkdir(parents=True)
        _write_zoom_config(TILEMAKER_CONFIG, config, zoom)
        run([
            "tilemaker",
            "--input", str(clipped),
            "--output", str(output),
            "--config", str(config),
            "--process", str(TILEMAKER_PROCESS),
            "--store", str(store),
            "--bbox", bbox_text,
        ])
        print(f"z{zoom}: {output} ({output.stat().st_size:,} bytes)")

    print(f"samples: {root}")
    return root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default="north-america/us/michigan")
    parser.add_argument("--bbox", type=_parse_bbox, required=True)
    parser.add_argument("--zooms", default="14,15", help="comma-separated max zooms")
    args = parser.parse_args()
    try:
        zooms = sorted({int(value.strip()) for value in args.zooms.split(",") if value.strip()})
    except ValueError as exc:
        parser.error(f"invalid --zooms: {exc}")
    if not zooms or any(zoom < 0 or zoom > 20 for zoom in zooms):
        parser.error("zooms must be between 0 and 20")
    build_samples(args.region, args.bbox, zooms)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
