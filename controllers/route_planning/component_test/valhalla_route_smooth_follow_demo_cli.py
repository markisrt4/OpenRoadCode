# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Simulate smooth navigation along a Valhalla route."""

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

DEFAULT_SPEED_MPH = 300.0
DEFAULT_UPDATE_HZ = 20.0
DEFAULT_ZOOM = 16.5
DEFAULT_PITCH = 45.0

DEFAULT_POSITION_SMOOTHING = 0.20
DEFAULT_BEARING_SMOOTHING = 0.12
DEFAULT_LOOKAHEAD_METERS = 30.0

EARTH_RADIUS_METERS = 6_371_000.0
METERS_PER_MILE = 1609.344


def distance_meters(
    start: GeoPoint,
    end: GeoPoint,
) -> float:
    """Calculate great-circle distance between two points."""

    lat1 = math.radians(start.latitude)
    lat2 = math.radians(end.latitude)

    delta_lat = math.radians(
        end.latitude - start.latitude
    )
    delta_lon = math.radians(
        end.longitude - start.longitude
    )

    a = (
        math.sin(delta_lat / 2.0) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2.0) ** 2
    )

    c = 2.0 * math.atan2(
        math.sqrt(a),
        math.sqrt(1.0 - a),
    )

    return EARTH_RADIUS_METERS * c


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


def interpolate_point(
    start: GeoPoint,
    end: GeoPoint,
    fraction: float,
) -> GeoPoint:
    """Interpolate between nearby route points."""

    fraction = max(
        0.0,
        min(1.0, fraction),
    )

    return GeoPoint(
        latitude=(
            start.latitude
            + (
                end.latitude
                - start.latitude
            )
            * fraction
        ),
        longitude=(
            start.longitude
            + (
                end.longitude
                - start.longitude
            )
            * fraction
        ),
    )


def smooth_value(
    current: float,
    target: float,
    factor: float,
) -> float:
    """Apply exponential smoothing to a scalar value."""

    return (
        current
        + (target - current)
        * factor
    )


def shortest_angle_delta(
    current: float,
    target: float,
) -> float:
    """Return shortest signed angular difference."""

    return (
        (target - current + 180.0)
        % 360.0
    ) - 180.0


def smooth_bearing(
    current: float,
    target: float,
    factor: float,
) -> float:
    """Smooth bearing across the 0/360-degree boundary."""

    delta = shortest_angle_delta(
        current,
        target,
    )

    return (
        current
        + delta * factor
    ) % 360.0


def find_lookahead_point(
    shape: tuple[GeoPoint, ...],
    start_index: int,
    current_position: GeoPoint,
    lookahead_meters: float,
) -> GeoPoint:
    """Find a route point roughly lookahead_meters ahead."""

    remaining = lookahead_meters
    previous = current_position

    for index in range(
        start_index + 1,
        len(shape),
    ):
        point = shape[index]

        segment_distance = distance_meters(
            previous,
            point,
        )

        if segment_distance >= remaining:
            if segment_distance <= 0.001:
                return point

            fraction = (
                remaining
                / segment_distance
            )

            return interpolate_point(
                previous,
                point,
                fraction,
            )

        remaining -= segment_distance
        previous = point

    return shape[-1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate smooth vehicle movement "
            "along a Valhalla route."
        )
    )

    parser.add_argument(
        "--url",
        default=ValhallaHttpClient.DEFAULT_BASE_URL,
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
        "--speed-mph",
        type=float,
        default=DEFAULT_SPEED_MPH,
    )

    parser.add_argument(
        "--update-hz",
        type=float,
        default=DEFAULT_UPDATE_HZ,
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

    parser.add_argument(
        "--position-smoothing",
        type=float,
        default=DEFAULT_POSITION_SMOOTHING,
        help=(
            "Position smoothing factor from 0 to 1. "
            "Lower values are smoother."
        ),
    )

    parser.add_argument(
        "--bearing-smoothing",
        type=float,
        default=DEFAULT_BEARING_SMOOTHING,
        help=(
            "Bearing smoothing factor from 0 to 1. "
            "Lower values are smoother."
        ),
    )

    parser.add_argument(
        "--lookahead-meters",
        type=float,
        default=DEFAULT_LOOKAHEAD_METERS,
        help=(
            "Distance ahead used to calculate "
            "vehicle heading."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.speed_mph <= 0.0:
        print(
            "--speed-mph must be greater than zero"
        )
        return 1

    if args.update_hz <= 0.0:
        print(
            "--update-hz must be greater than zero"
        )
        return 1

    if not 0.0 < args.position_smoothing <= 1.0:
        print(
            "--position-smoothing must be "
            "greater than 0 and at most 1"
        )
        return 1

    if not 0.0 < args.bearing_smoothing <= 1.0:
        print(
            "--bearing-smoothing must be "
            "greater than 0 and at most 1"
        )
        return 1

    if args.lookahead_meters <= 0.0:
        print(
            "--lookahead-meters must be greater than zero"
        )
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
            "Route has insufficient shape data"
        )
        return 1

    speed_mps = (
        args.speed_mph
        * METERS_PER_MILE
        / 3600.0
    )

    update_period = (
        1.0
        / args.update_hz
    )

    distance_per_update = (
        speed_mps
        * update_period
    )

    print(
        f"Route: "
        f"{route.distance_miles:.1f} miles, "
        f"{route.duration_seconds / 60.0:.0f} minutes"
    )

    print(
        f"Simulation: "
        f"{args.speed_mph:.1f} mph "
        f"at {args.update_hz:.1f} Hz"
    )

    print(
        f"Position smoothing: "
        f"{args.position_smoothing:.2f}"
    )

    print(
        f"Bearing smoothing: "
        f"{args.bearing_smoothing:.2f}"
    )

    print(
        f"Heading lookahead: "
        f"{args.lookahead_meters:.0f} m"
    )

    map_renderer = MapRendererClient()

    try:
        present_route(
            route=route,
            map_renderer=map_renderer,
        )

        time.sleep(1.0)

        shape = route.shape

        segment_index = 0
        segment_progress = 0.0

        position = shape[0]

        display_latitude = (
            position.latitude
        )
        display_longitude = (
            position.longitude
        )

        lookahead_point = find_lookahead_point(
            shape=shape,
            start_index=0,
            current_position=position,
            lookahead_meters=args.lookahead_meters,
        )

        bearing = calculate_bearing(
            position,
            lookahead_point,
        )

        print(
            "Starting smooth navigation demo..."
        )

        while (
            segment_index
            < len(shape) - 1
        ):
            frame_start = (
                time.monotonic()
            )

            remaining_distance = (
                distance_per_update
            )

            while (
                remaining_distance > 0.0
                and segment_index
                < len(shape) - 1
            ):
                start = (
                    shape[segment_index]
                )

                end = (
                    shape[
                        segment_index + 1
                    ]
                )

                segment_length = (
                    distance_meters(
                        start,
                        end,
                    )
                )

                if segment_length <= 0.001:
                    segment_index += 1
                    segment_progress = 0.0
                    continue

                distance_left = (
                    segment_length
                    * (
                        1.0
                        - segment_progress
                    )
                )

                if (
                    remaining_distance
                    >= distance_left
                ):
                    remaining_distance -= (
                        distance_left
                    )

                    segment_index += 1
                    segment_progress = 0.0

                    if (
                        segment_index
                        >= len(shape) - 1
                    ):
                        position = (
                            shape[-1]
                        )
                        break

                else:
                    segment_progress += (
                        remaining_distance
                        / segment_length
                    )

                    remaining_distance = 0.0

                    position = (
                        interpolate_point(
                            start,
                            end,
                            segment_progress,
                        )
                    )

            display_latitude = smooth_value(
                display_latitude,
                position.latitude,
                args.position_smoothing,
            )

            display_longitude = smooth_value(
                display_longitude,
                position.longitude,
                args.position_smoothing,
            )

            display_position = GeoPoint(
                latitude=display_latitude,
                longitude=display_longitude,
            )

            if (
                segment_index
                < len(shape) - 1
            ):
                lookahead_point = (
                    find_lookahead_point(
                        shape=shape,
                        start_index=segment_index,
                        current_position=position,
                        lookahead_meters=(
                            args.lookahead_meters
                        ),
                    )
                )

                target_bearing = (
                    calculate_bearing(
                        display_position,
                        lookahead_point,
                    )
                )

                bearing = smooth_bearing(
                    bearing,
                    target_bearing,
                    args.bearing_smoothing,
                )

            map_renderer.set_position(
                latitude=display_latitude,
                longitude=display_longitude,
            )

            map_renderer.set_camera(
                latitude=display_latitude,
                longitude=display_longitude,
                zoom=args.zoom,
                bearing=bearing,
                pitch=args.pitch,
            )

            print(
                f"\rSegment "
                f"{segment_index + 1}/"
                f"{len(shape) - 1} "
                f"heading={bearing:6.1f}°",
                end="",
                flush=True,
            )

            elapsed = (
                time.monotonic()
                - frame_start
            )

            sleep_time = (
                update_period
                - elapsed
            )

            if sleep_time > 0.0:
                time.sleep(
                    sleep_time
                )

        map_renderer.set_position(
            latitude=shape[-1].latitude,
            longitude=shape[-1].longitude,
        )

        map_renderer.set_camera(
            latitude=shape[-1].latitude,
            longitude=shape[-1].longitude,
            zoom=args.zoom,
            bearing=bearing,
            pitch=args.pitch,
        )

    except MapRendererUnavailableError as exc:
        print()
        print(
            f"Map renderer unavailable: {exc}"
        )
        return 1

    print()
    print(
        "Smooth navigation demo complete."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
