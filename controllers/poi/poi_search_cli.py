# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Command-line diagnostic for OpenRoadCode offline POI discovery and selection."""

from __future__ import annotations

import argparse
import math
import sys
import time

from controllers.poi import PoiCategory, PoiSearchController
from ui.navigation import GeoPoint


def _parse_category(value: str) -> PoiCategory:
    normalized = value.strip().upper()
    aliases = {
        "GAS": "FUEL",
        "RESTAURANT": "FOOD",
        "RESTAURANTS": "FOOD",
        "SUPERMARKET": "GROCERY",
    }
    normalized = aliases.get(normalized, normalized)
    try:
        return PoiCategory[normalized]
    except KeyError as exc:
        choices = ", ".join(category.name.casefold() for category in PoiCategory)
        raise argparse.ArgumentTypeError(
            f"unknown POI category {value!r}; choose from: {choices}"
        ) from exc


def _wait_for_search_result(
    controller: PoiSearchController,
    *,
    timeout_seconds: float,
):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        result = controller.poll_search_result()
        if result is not None:
            return result
        time.sleep(0.05)
    return None


def _wait_for_selected(
    controller: PoiSearchController,
    *,
    timeout_seconds: float,
):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        poi = controller.poll_selected()
        if poi is not None:
            return poi
        time.sleep(0.05)
    return None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Exercise renderer-independent offline POI discovery. "
            "Use --lat/--lon to override the current/cached navigation position. "
            "The ZeroMQ broker and native renderer are only required for --wait-selected."
        )
    )
    parser.add_argument(
        "category",
        type=_parse_category,
        help="POI category: food, fuel/gas, grocery, transit, or other",
    )
    parser.add_argument("--lat", type=float, help="search-center latitude in degrees")
    parser.add_argument("--lon", type=float, help="search-center longitude in degrees")
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="seconds to wait for the controller result (default: 5)",
    )
    parser.add_argument(
        "--settle",
        type=float,
        default=0.0,
        help="seconds to allow renderer selection subscriptions to settle (default: 0)",
    )
    parser.add_argument(
        "--wait-selected",
        action="store_true",
        help="after search, wait for a POI to be clicked in the native renderer",
    )
    parser.add_argument(
        "--selection-timeout",
        type=float,
        default=30.0,
        help="seconds to wait for a clicked POI when --wait-selected is used (default: 30)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.timeout <= 0 or args.settle < 0 or args.selection_timeout <= 0:
        print("timeouts must be positive and --settle must be non-negative", file=sys.stderr)
        return 2
    if (args.lat is None) != (args.lon is None):
        print("--lat and --lon must be supplied together", file=sys.stderr)
        return 2
    if args.lat is not None and not -90.0 <= args.lat <= 90.0:
        print("--lat must be between -90 and 90", file=sys.stderr)
        return 2
    if args.lon is not None and not -180.0 <= args.lon <= 180.0:
        print("--lon must be between -180 and 180", file=sys.stderr)
        return 2

    position_provider = None
    if args.lat is not None and args.lon is not None:
        position = GeoPoint(
            latitude_rad=math.radians(args.lat),
            longitude_rad=math.radians(args.lon),
        )
        position_provider = lambda: position

    controller = PoiSearchController(position_provider=position_provider)
    try:
        if args.settle:
            time.sleep(args.settle)

        category_name = args.category.name.casefold()
        if args.lat is not None:
            print(
                f"[poi-cli] searching category={category_name} "
                f"center={args.lat:.6f},{args.lon:.6f}",
                flush=True,
            )
        else:
            print(
                f"[poi-cli] searching category={category_name} "
                "center=current/cached-position",
                flush=True,
            )
        controller.search(args.category)

        result = _wait_for_search_result(controller, timeout_seconds=args.timeout)
        if result is None:
            print("[poi-cli] FAIL: controller produced no search result", file=sys.stderr)
            return 1

        print("[poi-cli] search result")
        print(f"  category: {result.category.name.casefold()}")
        print(f"  count:    {result.count}")
        print(
            "  bounds:   "
            f"south={result.south:.6f} west={result.west:.6f} "
            f"north={result.north:.6f} east={result.east:.6f}"
        )

        if not args.wait_selected:
            print("[poi-cli] PASS: offline POI search completed")
            return 0

        print(
            "[poi-cli] click a highlighted POI in the native map renderer...",
            flush=True,
        )
        poi = _wait_for_selected(
            controller,
            timeout_seconds=args.selection_timeout,
        )
        if poi is None:
            print(
                "[poi-cli] FAIL: no map.poi.selected event received before timeout",
                file=sys.stderr,
            )
            return 1

        print("[poi-cli] selected POI")
        print(f"  id:       {poi.poi_id}")
        print(f"  name:     {poi.name}")
        print(f"  category: {poi.category.name.casefold()}")
        print(f"  brand:    {poi.brand or '-'}")
        print(f"  class:    {poi.source_class or '-'}")
        print(f"  subclass: {poi.source_subclass or '-'}")
        print(
            "  position: "
            f"lat={math.degrees(poi.position.latitude_rad):.6f} "
            f"lon={math.degrees(poi.position.longitude_rad):.6f}"
        )
        if poi.actions:
            print("  actions:")
            for action in poi.actions:
                suffix = f" -> {action.uri}" if action.uri else ""
                print(f"    {action.kind.name.casefold()}: {action.label}{suffix}")
        else:
            print("  actions:  none")

        print("[poi-cli] PASS: offline search and renderer selection received")
        return 0
    finally:
        controller.close()


if __name__ == "__main__":
    raise SystemExit(main())
