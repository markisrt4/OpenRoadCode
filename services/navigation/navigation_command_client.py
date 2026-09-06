# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Typed client for navigation service commands."""

from __future__ import annotations

from typing import Any

import zmq

from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteManeuver,
    RouteRequest,
    RouteResult,
    TravelMode,
)
from services.navigation.navigation_command_service import (
    CALCULATE_ROUTE_COMMAND,
    SIMULATE_ROUTE_COMMAND,
    START_ROUTE_COMMAND,
    STOP_ROUTE_SIMULATION_COMMAND,
)
from services.navigation.zeromq_navigation_command_server import (
    DEFAULT_NAVIGATION_COMMAND_ENDPOINT,
)


class NavigationCommandUnavailableError(RuntimeError):
    """Raised when the navigation command service cannot be reached."""


class NavigationCommandError(RuntimeError):
    """Raised when the navigation service rejects a command."""


class NavigationCommandClient:
    """Send typed commands to the navigation service over ZeroMQ."""

    def __init__(
        self,
        endpoint: str = DEFAULT_NAVIGATION_COMMAND_ENDPOINT,
        *,
        timeout_ms: int = 2000,
    ) -> None:
        self._endpoint = endpoint
        self._timeout_ms = timeout_ms

    def calculate_route(self, request: RouteRequest) -> RouteResult:
        """Calculate a route through the navigation service."""
        response = self._request(
            CALCULATE_ROUTE_COMMAND,
            {
                "origin": self._encode_point(request.origin),
                "destination": self._encode_point(request.destination),
                "travel_mode": request.travel_mode.name,
            },
        )
        return self._route_from_response(response)

    def calculate_route_to(
        self,
        destination: str,
        *,
        travel_mode: TravelMode = TravelMode.AUTO,
    ) -> RouteResult:
        """Calculate a route from the current position to a text destination."""
        response = self._request(
            CALCULATE_ROUTE_COMMAND,
            {
                "destination": destination,
                "travel_mode": travel_mode.name,
            },
        )
        return self._route_from_response(response)

    def start_route_to(
        self,
        destination: str,
        *,
        travel_mode: TravelMode = TravelMode.AUTO,
    ) -> RouteResult:
        """Resolve a text destination and start guidance from the current position."""
        response = self._request(
            START_ROUTE_COMMAND,
            {
                "destination": destination,
                "travel_mode": travel_mode.name,
            },
        )
        return self._route_from_response(response)

    def simulate_active_route(self, *, time_scale: float = 60.0) -> None:
        """Drive configured simulated position input along the active route."""
        self._request(SIMULATE_ROUTE_COMMAND, {"time_scale": time_scale})

    def stop_route_simulation(self) -> None:
        """Return the navigation input to its normal simulation profile."""
        self._request(STOP_ROUTE_SIMULATION_COMMAND, {})

    @classmethod
    def _route_from_response(cls, response: dict[str, Any]) -> RouteResult:
        data = response.get("data")
        if not isinstance(data, dict):
            raise NavigationCommandError("Route response did not contain route data")
        return cls._decode_route(data)

    def _request(self, command: str, arguments: dict[str, Any]) -> dict[str, Any]:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.SNDTIMEO, self._timeout_ms)
        socket.setsockopt(zmq.RCVTIMEO, self._timeout_ms)
        try:
            socket.connect(self._endpoint)
            socket.send_json({"command": command, "arguments": arguments})
            response = socket.recv_json()
        except (zmq.Again, zmq.ZMQError, ValueError) as error:
            raise NavigationCommandUnavailableError(
                f"Navigation command service unavailable at {self._endpoint}"
            ) from error
        finally:
            socket.close(linger=0)
            context.term()

        if not isinstance(response, dict):
            raise NavigationCommandError("Navigation service returned an invalid response")
        if not response.get("ok", False):
            raise NavigationCommandError(
                str(response.get("message", "Navigation command failed"))
            )
        return response

    @staticmethod
    def _encode_point(point: GeoPoint) -> dict[str, float]:
        return {"latitude": point.latitude, "longitude": point.longitude}

    @staticmethod
    def _decode_route(data: dict[str, Any]) -> RouteResult:
        try:
            shape = tuple(
                GeoPoint(
                    latitude=float(point["latitude"]),
                    longitude=float(point["longitude"]),
                )
                for point in data["shape"]
            )
            maneuvers = tuple(
                RouteManeuver(
                    instruction=str(item["instruction"]),
                    verbal_instruction=(
                        None
                        if item.get("verbal_instruction") is None
                        else str(item["verbal_instruction"])
                    ),
                    distance_miles=float(item["distance_miles"]),
                    duration_seconds=float(item["duration_seconds"]),
                    begin_shape_index=int(item["begin_shape_index"]),
                    end_shape_index=int(item["end_shape_index"]),
                )
                for item in data["maneuvers"]
            )
            return RouteResult(
                distance_miles=float(data["distance_miles"]),
                duration_seconds=float(data["duration_seconds"]),
                shape=shape,
                maneuvers=maneuvers,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise NavigationCommandError(f"Invalid route response: {error}") from error
