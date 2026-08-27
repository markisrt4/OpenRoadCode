# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""CLI/TUI entrypoint for OpenRoadCode map-data generation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

from .build import OUTPUT_ROOT, build_regions
from .geofabrik import fetch_index, resolve_region_ids
from .selection import load_region_ids, save_region_ids
from .tui import select_regions
from .validate import ValidationError, validate_output

INDEX_PATH = Path(os.environ.get("OPENROAD_GEOFABRIK_INDEX", "/cache/geofabrik-index-v1-nogeom.json"))
SELECTION_PATH = Path(os.environ.get("OPENROAD_SELECTION_PATH", "/cache/selected-regions.json"))


def format_duration(seconds: float) -> str:
    total_seconds = max(0, round(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def format_size(size_bytes: int) -> str:
    value = float(size_bytes)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024
    raise AssertionError("unreachable")


def directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def print_build_summary(selected, elapsed_seconds: float) -> None:
    source_size = sum(
        (OUTPUT_ROOT / "maps/source" / f"{region.safe_id}.osm.pbf").stat().st_size
        for region in selected
    )
    print("\nBuild complete")
    print("  Regions: " + ", ".join(region.name for region in selected))
    print(f"  Region source data: {format_size(source_size)} ({source_size:,} bytes)")
    output_size = directory_size(OUTPUT_ROOT)
    print(f"  Deployable output: {format_size(output_size)} ({output_size:,} bytes)")
    print(f"  Build time: {format_duration(elapsed_seconds)}")
    print(f"  Output: {OUTPUT_ROOT}")


def print_validation_summary(result: dict, root: Path) -> None:
    """Print a concise human-readable validation result."""
    mbtiles = result["mbtiles"]
    valhalla = result["valhalla"]
    output_size = directory_size(root)
    mbtiles_path = root / "maps/vector/openroadcode.mbtiles"
    style_path = root / "maps/styles/openroadcode.json"
    extract_path = root / "valhalla/tiles.tar"

    print("\n========================================")
    print(" OpenRoadCode navigation data: PASS")
    print("========================================")
    print(f"  Deployable size:       {format_size(output_size)} ({output_size:,} bytes)")
    print(f"  Source PBF files:      {result['source_pbfs']}")
    print(f"  MBTiles size:          {format_size(mbtiles_path.stat().st_size)}")
    print(f"  Vector tiles:          {mbtiles['tiles']:,}")
    print(f"  Vector layers:         {len(mbtiles['layers'])}")
    print(f"  Glyph files:           {result['glyph_files']:,}")
    print(f"  Style:                 {style_path.name}")
    print(f"  Valhalla tile files:   {valhalla['tile_files']:,}")
    print(f"  Valhalla extract:      {format_size(extract_path.stat().st_size)}")
    print(f"  Valhalla service:      {valhalla.get('service_status', 'not tested')}")
    print("  SQLite integrity:      PASS")
    print("  Required map sources:  PASS")
    print("  Checksums:             PASS")
    print(f"  Output:                {root}")


def run_build(selected, *, clean: bool, service_smoke: bool) -> tuple[dict, float]:
    started = time.monotonic()
    result = build_regions(selected, clean=clean, service_smoke=service_smoke)
    return result, time.monotonic() - started


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build offline OpenRoadCode map and Valhalla data")
    parser.add_argument("--refresh-index", action="store_true", help="refresh Geofabrik's region catalog")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("tui", help="interactive multi-region selector")
    build = sub.add_parser("build", help="build one or more region IDs")
    build.add_argument("--regions", required=True, help="comma-separated Geofabrik IDs")
    build.add_argument("--no-clean", action="store_true", help="do not clean prior generated output")
    build.add_argument("--no-service-smoke", action="store_true", help="skip Valhalla /status smoke test")
    validate = sub.add_parser("validate", help="validate existing generated output")
    validate.add_argument("--service-smoke", action="store_true")
    validate.add_argument("--json", action="store_true", help="also print raw validation JSON")
    sub.add_parser("list", help="list selectable Geofabrik region IDs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = args.command or "tui"
    try:
        if command == "validate":
            result = validate_output(OUTPUT_ROOT, service_smoke=args.service_smoke)
            if args.json:
                print(json.dumps(result, indent=2))
            print_validation_summary(result, OUTPUT_ROOT)
            return 0
        regions = fetch_index(INDEX_PATH, refresh=args.refresh_index)
        if command == "list":
            for region in regions:
                print(f"{region.id}\t{region.name}")
            return 0
        if command == "build":
            selected = resolve_region_ids(regions, [x.strip() for x in args.regions.split(",") if x.strip()])
            result, elapsed = run_build(
                selected,
                clean=not args.no_clean,
                service_smoke=not args.no_service_smoke,
            )
            print(json.dumps(result, indent=2))
            print_build_summary(selected, elapsed)
            return 0
        try:
            saved_region_ids = load_region_ids(SELECTION_PATH)
        except (OSError, ValueError) as exc:
            print(f"Warning: ignoring saved region selection: {exc}", file=sys.stderr)
            saved_region_ids = set()
        selected = select_regions(regions, saved_region_ids)
        if selected is None:
            print("Cancelled")
            return 0
        try:
            save_region_ids(SELECTION_PATH, (region.id for region in selected))
        except OSError as exc:
            print(f"Warning: could not save region selection: {exc}", file=sys.stderr)
        print("Selected:")
        for region in selected:
            print(f"  {region.id}: {region.name}")
        answer = input("Build these regions now? [y/N] ").strip().lower()
        if answer != "y":
            print("Cancelled")
            return 0
        result, elapsed = run_build(selected, clean=True, service_smoke=True)
        print(json.dumps(result, indent=2))
        print_build_summary(selected, elapsed)
        return 0
    except (ValueError, ValidationError, RuntimeError) as exc:
        print("\n========================================", file=sys.stderr)
        print(" OpenRoadCode navigation data: FAIL", file=sys.stderr)
        print("========================================", file=sys.stderr)
        print(f"  Reason: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nCancelled", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
