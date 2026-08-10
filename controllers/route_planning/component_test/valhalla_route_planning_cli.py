"""Physical component test for Valhalla route planning."""

from __future__ import annotations

import argparse

from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteRequest,
)
from controllers.route_planning.valhalla_route_planning_controller import (
    ValhallaRoutePlanningController,
)
from protocols.valhalla.valhalla_http_client import (
    ValhallaHttpClient,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate a route using a running "
            "Valhalla service"
        )
    )

    parser.add_argument(
        "--url",
        default=ValhallaHttpClient.DEFAULT_BASE_URL,
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

    controller = ValhallaRoutePlanningController(
        client=ValhallaHttpClient(
            base_url=args.url,
        )
    )

    if not controller.is_available:
        print(
            controller.status_message
            or "Valhalla is unavailable"
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
        f"Distance: "
        f"{route.distance_miles:.1f} miles"
    )
    print(
        f"Duration: "
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

        if maneuver.verbal_instruction:
            print(
                "    Voice: "
                f"{maneuver.verbal_instruction}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

