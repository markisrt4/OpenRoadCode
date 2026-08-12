# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse

from controllers.navigation.navigation_types import (
    GeoPoint,
    RouteRequest,
)
from controllers.navigation.valhalla_navigation_controller import (
    ValhallaNavigationController,
)
from protocols.valhalla.valhalla_http_client import (
    ValhallaHttpClient,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test Valhalla route calculation"
    )

    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8002",
        help="Valhalla service base URL",
    )

    parser.add_argument(
        "--origin-lat",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--origin-lon",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--destination-lat",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--destination-lon",
        type=float,
        required=True,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    controller = ValhallaNavigationController(
        client=ValhallaHttpClient(
            base_url=args.url,
        )
    )

    if not controller.is_available():
        print(
            f"Valhalla is unavailable at {args.url}"
        )
        return 1

    route = controller.calculate_route(
        RouteRequest(
            origin=GeoPoint(
                latitude=args.origin_lat,
                longitude=args.origin_lon,
            ),
            destination=GeoPoint(
                latitude=args.destination_lat,
                longitude=args.destination_lon,
            ),
        )
    )

    print()
    print("Route")
    print("-----")
    print(
        f"Distance: {route.distance_miles:.1f} miles"
    )
    print(
        "Duration: "
        f"{route.duration_seconds / 60.0:.0f} minutes"
    )
    print(
        f"Shape points: {len(route.shape)}"
    )

    print()
    print("Maneuvers")
    print("---------")

    for number, maneuver in enumerate(
        route.maneuvers,
        start=1,
    ):
        print(
            f"{number:2}. "
            f"{maneuver.instruction}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
