"""CLI/TUI entrypoint for OpenRoadCode map-data generation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .build import OUTPUT_ROOT, build_regions
from .geofabrik import fetch_index, resolve_region_ids
from .tui import select_regions
from .validate import ValidationError, validate_output

INDEX_PATH = Path(os.environ.get("OPENROAD_GEOFABRIK_INDEX", "/cache/geofabrik-index-v1-nogeom.json"))


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
    sub.add_parser("list", help="list selectable Geofabrik region IDs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = args.command or "tui"
    try:
        if command == "validate":
            result = validate_output(OUTPUT_ROOT, service_smoke=args.service_smoke)
            print(json.dumps(result, indent=2))
            return 0
        regions = fetch_index(INDEX_PATH, refresh=args.refresh_index)
        if command == "list":
            for region in regions:
                print(f"{region.id}\t{region.name}")
            return 0
        if command == "build":
            selected = resolve_region_ids(regions, [x.strip() for x in args.regions.split(",") if x.strip()])
            result = build_regions(selected, clean=not args.no_clean, service_smoke=not args.no_service_smoke)
            print(json.dumps(result, indent=2))
            return 0
        selected = select_regions(regions)
        if selected is None:
            print("Cancelled")
            return 0
        print("Selected:")
        for region in selected:
            print(f"  {region.id}: {region.name}")
        answer = input("Build these regions now? [y/N] ").strip().lower()
        if answer != "y":
            print("Cancelled")
            return 0
        result = build_regions(selected, clean=True, service_smoke=True)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, ValidationError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nCancelled", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
