# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""CLI/TUI entrypoint for OpenRoadCode map-data generation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import subprocess
import time

from .map_3d import PRESETS
from .build import OUTPUT_ROOT, _write_manifest, build_regions
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


def reusable_build_for_regions(selected, *, root: Path, service_smoke: bool) -> dict | None:
    """Return validation data when an existing build matches the requested regions."""
    manifest_path = root / "build-manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None

    manifest_regions = manifest.get("regions")
    if not isinstance(manifest_regions, list):
        return None
    existing_ids = sorted(
        item.get("id") for item in manifest_regions if isinstance(item, dict) and item.get("id")
    )
    requested_ids = sorted(region.id for region in selected)
    if existing_ids != requested_ids:
        return None

    try:
        return validate_output(root, service_smoke=service_smoke)
    except (OSError, ValueError, ValidationError, RuntimeError):
        return None


def run_build(selected, *, clean: bool, service_smoke: bool) -> tuple[dict, float]:
    started = time.monotonic()
    result = build_regions(selected, clean=clean, service_smoke=service_smoke)
    return result, time.monotonic() - started


def build_or_reuse(selected, *, clean: bool, service_smoke: bool, force: bool) -> tuple[dict, float, bool]:
    if not force:
        result = reusable_build_for_regions(
            selected,
            root=OUTPUT_ROOT,
            service_smoke=service_smoke,
        )
        if result is not None:
            print("Existing validated build matches requested regions; reusing it.")
            return result, 0.0, True
    result, elapsed = run_build(selected, clean=clean, service_smoke=service_smoke)
    return result, elapsed, False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build offline OpenRoadCode map and Valhalla data")
    parser.add_argument("--refresh-index", action="store_true", help="refresh Geofabrik's region catalog")
    sub = parser.add_subparsers(dest="command")
    tui = sub.add_parser("tui", help="interactive multi-region selector")
    tui.add_argument("--force", action="store_true", help="rebuild even when matching validated output exists")
    build = sub.add_parser("build", help="build one or more region IDs")
    build.add_argument("--regions", required=True, help="comma-separated Geofabrik IDs")
    build.add_argument("--no-clean", action="store_true", help="do not clean prior generated output")
    build.add_argument("--no-service-smoke", action="store_true", help="skip Valhalla /status smoke test")
    build.add_argument("--force", action="store_true", help="rebuild even when matching validated output exists")
    validate = sub.add_parser("validate", help="validate existing generated output")
    validate.add_argument("--service-smoke", action="store_true")
    validate.add_argument("--json", action="store_true", help="also print raw validation JSON")
    validate.add_argument(
        "--regions",
        help="comma-separated Geofabrik IDs describing the validated output",
    )
    validate.add_argument("--installed-regions", action="store_true",
                          help="recover region IDs from installed source PBF filenames")
    validate.add_argument(
        "--write-manifest",
        action="store_true",
        help="write a fresh manifest after successful validation; requires --regions or --installed-regions",
    )
    map3d = sub.add_parser("3d", help="build optional 3D buildings from installed navigation sources")
    map3d.add_argument("--coverage", choices=tuple(PRESETS))
    map3d.add_argument("--layer", choices=("buildings","terrain"), default="buildings", help="optional offline layer to build")
    map3d.add_argument("--yes", action="store_true", help="confirm non-interactive 3D build; requires --coverage")
    sub.add_parser("list", help="list selectable Geofabrik region IDs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = args.command or "tui"
    try:
        if command == "3d":
            from .map_3d import PRESETS, build_pack
            from .map_3d_menu import choose_coverage
            if args.yes and not args.coverage:
                raise ValueError("--yes requires --coverage")
            coverage = args.coverage or choose_coverage(layer=getattr(args, 'layer', 'buildings'))
            if coverage is None:
                print("Cancelled")
                return 0
            previous_path = OUTPUT_ROOT / "build-manifest.json"
            previous_bytes = previous_path.read_bytes()
            previous = json.loads(previous_bytes)
            if previous.get("schema") != 2:
                raise ValueError("Build a validated schema-2 navigation dataset before adding 3D packs")
            baseline = validate_output(OUTPUT_ROOT, service_smoke=False)
            layer = getattr(args, 'layer', 'buildings')
            pack_id = coverage if layer == 'buildings' else coverage+'-terrain'
            print(f"Coverage: {PRESETS[coverage][0]} · {PRESETS[coverage][1]}")
            if layer == 'terrain':
                print("Layer: terrain. Downloads 65×65 USGS 3DEP samples; Internet required on the build host.")
                print("Relative relief in metres; source datum is preserved. Terrain payload capped at 2 MiB.")
            else:
                print("Layer: buildings. Uses existing OSM sources; no download. Output size is known after extraction.")
                print("Limit: 8 tiles, 10 MiB geometry each plus metadata; complex polygons are omitted.")
            if not args.yes and input("Build this optional pack now? [y/N] ").strip().lower() != 'y':
                print("Cancelled")
                return 0
            existing = OUTPUT_ROOT/'maps/3d/packs'/pack_id
            if existing.exists():
                from .map_3d import validate_pack
                record = validate_pack(existing)
                if (previous.get('map_3d') or {}).get(pack_id) != record:
                    raise ValueError('Existing 3D pack is not certified by the dataset manifest; validate it before publishing')
                print(f"Reusing certified {layer} pack: {format_size(record['bytes'])}")
                return 0
            # A complete dataset must not retain a valid old certificate while being changed.
            previous_path.unlink()
            try:
                if layer == 'terrain':
                    from .terrain import download
                    download(existing, coverage)
                    destination = existing
                else:
                    destination = build_pack(OUTPUT_ROOT, coverage)
                result = validate_output(OUTPUT_ROOT, service_smoke=False)
            except BaseException:
                # Extraction only touches temporary files. Restore the certificate
                # only after proving that the original dataset is unchanged.
                if not existing.exists() and validate_output(OUTPUT_ROOT, service_smoke=False) == baseline:
                    previous_path.write_bytes(previous_bytes)
                raise
            # Preserve region/search metadata while certifying all new artifacts.
            previous['validation'] = result
            previous['map_3d'] = result['map_3d']
            previous['deployable_bytes'] = sum(p.stat().st_size for p in OUTPUT_ROOT.rglob('*') if p.is_file() and p.name != 'build-manifest.json')
            previous['generated_unix'] = max(int(time.time()),previous.get('generated_unix',0)+1)
            temporary = previous_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(previous,indent=2))
            temporary.replace(previous_path)
            record = result['map_3d'][pack_id]
            print(f"3D {layer} pack built: {format_size(record['bytes'])} at {destination}")
            print("Publish and pull using the existing navigation deployment tools.")
            return 0
        if command == "validate":
            if args.installed_regions:
                if args.regions:
                    raise ValueError("Choose --regions or --installed-regions, not both")
                args.regions = ','.join(p.name.removesuffix('.osm.pbf').replace('__','/')
                    for p in sorted((OUTPUT_ROOT/'maps/source').glob('*.osm.pbf')))
            if args.write_manifest and not args.regions:
                raise ValueError("--write-manifest requires --regions")
            result = validate_output(OUTPUT_ROOT, service_smoke=args.service_smoke)
            if args.write_manifest:
                regions = fetch_index(INDEX_PATH, refresh=args.refresh_index)
                selected = resolve_region_ids(
                    regions,
                    [x.strip() for x in args.regions.split(",") if x.strip()],
                )
                if len(selected) != result["source_pbfs"]:
                    raise ValidationError(
                        "Region count does not match validated source PBF count: "
                        f"{len(selected)} region(s) vs {result['source_pbfs']} PBF(s)"
                    )
                search_counts = {}
                existing_manifest = OUTPUT_ROOT / "build-manifest.json"
                if existing_manifest.is_file():
                    try:
                        previous = json.loads(existing_manifest.read_text(encoding="utf-8"))
                        search_counts = (previous.get("search_index") or {}).get("counts") or {}
                    except (OSError, json.JSONDecodeError, TypeError):
                        pass
                _write_manifest(selected, result, search_counts)
                print(f"Wrote validated manifest: {OUTPUT_ROOT / 'build-manifest.json'}")
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
            result, elapsed, reused = build_or_reuse(
                selected,
                clean=not args.no_clean,
                service_smoke=not args.no_service_smoke,
                force=args.force,
            )
            print(json.dumps(result, indent=2))
            if reused:
                print_validation_summary(result, OUTPUT_ROOT)
            else:
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
        result, elapsed, reused = build_or_reuse(
            selected,
            clean=True,
            service_smoke=True,
            force=getattr(args, "force", False),
        )
        print(json.dumps(result, indent=2))
        if reused:
            print_validation_summary(result, OUTPUT_ROOT)
        else:
            print_build_summary(selected, elapsed)
        return 0
    except (OSError, ValueError, ValidationError, RuntimeError, subprocess.SubprocessError) as exc:
        print("\n========================================", file=sys.stderr)
        print(" OpenRoadCode navigation data: FAIL", file=sys.stderr)
        print("========================================", file=sys.stderr)
        print(f"  Reason: {exc}", file=sys.stderr)
        return 2
    except EOFError:
        print("Cancelled", file=sys.stderr)
        return 0
    except KeyboardInterrupt:
        print("\nCancelled", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
