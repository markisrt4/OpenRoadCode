# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Command-line diagnostic for the live OpenRoadCode POI pipeline."""

from __future__ import annotations

import argparse
import math
import sys
import time

from controllers.poi import PoiCategory, PoiSearchController


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
            "Exercise the live map-renderer POI protocol without the ORC Tk UI. "
            "The ZeroMQ broker and native map renderer must already be running."
        )
    )
    parser.add_argument(
        "category",
        type=_parse_category,
        help="POI category: food, fuel/gas, grocery, transit, or other",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="seconds to wait for a POI search result (default: 5)",
    )
    parser.add_argument(
        "--settle",
        type=float,
        default=0.5,
        help="seconds to let ZeroMQ subscriptions connect before searching (default: 0.5)",
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

    controller = PoiSearchController()
    try:
        if args.settle:
            time.sleep(args.settle)

        category_name = args.category.name.casefold()
        print(f"[poi-cli] searching category={category_name}", flush=True)
        controller.search(args.category)

        result = _wait_for_search_result(controller, timeout_seconds=args.timeout)
        if result is None:
            print(
                "[poi-cli] FAIL: no map.poi.search_result received. "
                "Check that the ZeroMQ broker and native map renderer are running.",
                file=sys.stderr,
            )
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
            print("[poi-cli] PASS: renderer search response received")
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

        print("[poi-cli] PASS: search and selection pipeline received")
        return 0
    finally:
        controller.close()


if __name__ == "__main__":
    raise SystemExit(main())
