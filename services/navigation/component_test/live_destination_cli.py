# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Send a text destination to a running OpenRoadCode navigation service."""

from __future__ import annotations

import argparse

from controllers.route_planning.route_planning_types import TravelMode
from services.navigation.navigation_command_client import (
    NavigationCommandClient,
    NavigationCommandError,
    NavigationCommandUnavailableError,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve a text destination through the running navigation service "
            "and calculate or start a route from the current navigation position."
        )
    )
    parser.add_argument("destination", help="Place name or street address")
    parser.add_argument(
        "--start",
        action="store_true",
        help="Start route guidance instead of only calculating the route",
    )
    parser.add_argument(
        "--travel-mode",
        choices=tuple(mode.name for mode in TravelMode),
        default=TravelMode.AUTO.name,
    )
    parser.add_argument(
        "--endpoint",
        help="Override the navigation command ZeroMQ endpoint",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    client = (
        NavigationCommandClient(endpoint=args.endpoint)
        if args.endpoint
        else NavigationCommandClient()
    )
    travel_mode = TravelMode[args.travel_mode]

    try:
        if args.start:
            route = client.start_route_to(args.destination, travel_mode=travel_mode)
            action = "started"
        else:
            route = client.calculate_route_to(args.destination, travel_mode=travel_mode)
            action = "calculated"
    except (NavigationCommandError, NavigationCommandUnavailableError) as error:
        print(f"Navigation request failed: {error}")
        return 1

    print(f"Navigation route {action}")
    print(f"  destination: {args.destination}")
    print(f"  distance:    {route.distance_miles:.1f} miles")
    print(f"  duration:    {route.duration_seconds / 60.0:.1f} minutes")
    print(f"  maneuvers:   {len(route.maneuvers)}")
    if route.maneuvers:
        print(f"  first:       {route.maneuvers[0].instruction}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
