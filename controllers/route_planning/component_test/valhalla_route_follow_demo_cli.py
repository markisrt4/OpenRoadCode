# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Simulate turn-by-turn navigation along a Valhalla route."""

from __future__ import annotations

import argparse
import math
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

DEFAULT_ZOOM = 16.5
DEFAULT_PITCH = 45.0


def calculate_bearing(
    start: GeoPoint,
    end: GeoPoint,
) -> float:
    """Calculate initial bearing from start to end."""

    lat1 = math.radians(start.latitude)
    lat2 = math.radians(end.latitude)

    delta_lon = math.radians(
        end.longitude - start.longitude
    )

    x = (
        math.sin(delta_lon)
        * math.cos(lat2)
    )

    y = (
        math.cos(lat1)
        * math.sin(lat2)
        - math.sin(lat1)
        * math.cos(lat2)
        * math.cos(delta_lon)
    )

    bearing = math.degrees(
        math.atan2(x, y)
    )

    return (bearing + 360.0) % 360.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate a Valhalla route and simulate "
            "a vehicle using a navigation follow camera."
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
        help="Delay between position updates.",
    )

    parser.add_argument(
        "--step",
        type=int,
        default=5,
        help="Use every Nth route shape point.",
    )

    parser.add_argument(
        "--zoom",
        type=float,
        default=DEFAULT_ZOOM,
    )

    parser.add_argument(
        "--pitch",
        type=float,
        default=DEFAULT_PITCH,
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

    if len(route.shape) < 2:
        print(
            "Calculated route does not contain "
            "enough shape points"
        )
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
        # Start by showing the driver the complete route.
        present_route(
            route=route,
            map_renderer=map_renderer,
        )

        time.sleep(1.0)

        animation_points = list(
            route.shape[::args.step]
        )

        # Ensure the actual destination is included even
        # when --step skips over the final shape point.
        if animation_points[-1] != route.shape[-1]:
            animation_points.append(
                route.shape[-1]
            )

        print("Starting navigation follow demo...")

        previous_bearing = calculate_bearing(
            animation_points[0],
            animation_points[1],
        )

        for index, point in enumerate(
            animation_points
        ):
            if index + 1 < len(animation_points):
                next_point = animation_points[
                    index + 1
                ]

                bearing = calculate_bearing(
                    point,
                    next_point,
                )

                previous_bearing = bearing

            else:
                bearing = previous_bearing

            map_renderer.set_position(
                latitude=point.latitude,
                longitude=point.longitude,
            )

            map_renderer.set_camera(
                latitude=point.latitude,
                longitude=point.longitude,
                zoom=args.zoom,
                bearing=bearing,
                pitch=args.pitch,
            )

            print(
                f"\rPosition "
                f"{index + 1}/"
                f"{len(animation_points)} "
                f"heading={bearing:6.1f}°",
                end="",
                flush=True,
            )

            time.sleep(
                args.delay
            )

    except MapRendererUnavailableError as exc:
        print()
        print(
            f"Map renderer unavailable: {exc}"
        )
        return 1

    print()
    print("Navigation follow demo complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
