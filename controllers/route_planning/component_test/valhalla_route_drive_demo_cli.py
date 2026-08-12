# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Animate a simulated vehicle along a Valhalla route."""

from __future__ import annotations

import argparse
import time

from controllers.route_planning.route_map_presenter import (
    present_route,
)
from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteRequest,
)
from controllers.route_planning.valhalla_route_planning_controller import (
    ValhallaRoutePlanningController,
)
from protocols.map_renderer.map_renderer_client import (
    MapRendererClient,
    MapRendererUnavailableError,
)
from protocols.valhalla.valhalla_http_client import (
    ValhallaHttpClient,
)


DEFAULT_ORIGIN_LAT = 42.3500
DEFAULT_ORIGIN_LON = -83.1000

DEFAULT_DESTINATION_LAT = 42.3314
DEFAULT_DESTINATION_LON = -83.0458


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate a Valhalla route and animate "
            "a simulated vehicle along it."
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
        default=DEFAULT_ORIGIN_LAT,
    )

    parser.add_argument(
        "--origin-lon",
        type=float,
        default=DEFAULT_ORIGIN_LON,
    )

    parser.add_argument(
        "--destination-lat",
        type=float,
        default=DEFAULT_DESTINATION_LAT,
    )

    parser.add_argument(
        "--destination-lon",
        type=float,
        default=DEFAULT_DESTINATION_LON,
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.05,
        help=(
            "Delay in seconds between vehicle "
            "position updates."
        ),
    )

    parser.add_argument(
        "--step",
        type=int,
        default=1,
        help=(
            "Use every Nth route shape point. "
            "Higher values make the demo faster."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.delay < 0.0:
        print("--delay must be zero or greater")
        return 1

    if args.step < 1:
        print("--step must be at least 1")
        return 1

    print("Connecting to Valhalla...")

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

    print("Calculating route...")

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

    if not route.shape:
        print("Calculated route has no shape points")
        return 1

    print(
        f"Route: {route.distance_miles:.1f} miles, "
        f"{route.duration_seconds / 60.0:.0f} minutes"
    )

    print(
        f"Shape points: {len(route.shape)}"
    )

    map_renderer = MapRendererClient()

    try:
        print("Presenting route...")

        present_route(
            route=route,
            map_renderer=map_renderer,
        )

        # Give the camera a moment to finish the
        # fit-bounds animation before moving the vehicle.
        time.sleep(0.75)

        print("Starting simulated drive...")

        animation_points = route.shape[
            ::args.step
        ]

        for index, point in enumerate(
            animation_points,
            start=1,
        ):
            map_renderer.set_position(
                latitude=point.latitude,
                longitude=point.longitude,
            )

            print(
                f"\rPosition "
                f"{index}/{len(animation_points)}",
                end="",
                flush=True,
            )

            time.sleep(
                args.delay
            )

        # Make certain we end exactly at the
        # calculated destination point.
        final_point = route.shape[-1]

        map_renderer.set_position(
            latitude=final_point.latitude,
            longitude=final_point.longitude,
        )

    except MapRendererUnavailableError as exc:
        print()
        print(
            f"Map renderer unavailable: {exc}"
        )
        return 1

    print()
    print("Simulated drive complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
