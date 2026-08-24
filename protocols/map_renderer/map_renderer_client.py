# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Client for controlling the native OpenRoadCode map renderer."""

from __future__ import annotations

import json

import zmq

from .map_renderer_protocol import MapRendererCommand

DEFAULT_MAP_RENDERER_ENDPOINT = "ipc:///tmp/openroadcode-map-renderer"


class MapRendererUnavailableError(RuntimeError):
    """Raised when the native map renderer is unavailable."""


class MapRendererCommandError(RuntimeError):
    """Raised when the native map renderer rejects a command."""


class MapRendererClient:
    """Send request/reply commands to the native map renderer."""

    def __init__(
        self,
        endpoint: str = DEFAULT_MAP_RENDERER_ENDPOINT,
        *,
        timeout_ms: int = 1000,
    ) -> None:
        self._endpoint = endpoint
        self._timeout_ms = timeout_ms

    def set_camera(self, latitude: float, longitude: float, zoom: float,
                   bearing: float = 0.0, pitch: float = 0.0) -> None:
        self._send_command({"command": MapRendererCommand.SET_CAMERA,
                            "latitude": latitude, "longitude": longitude,
                            "zoom": zoom, "bearing": bearing, "pitch": pitch})

    def set_route(self, geojson: dict[str, object]) -> None:
        self._send_command({"command": MapRendererCommand.SET_ROUTE,
                            "geojson": geojson})

    def set_center(self, latitude: float, longitude: float) -> None:
        self._send_command({"command": MapRendererCommand.SET_CENTER,
                            "latitude": latitude, "longitude": longitude})

    def set_position(self, latitude: float, longitude: float) -> None:
        self._send_command({"command": MapRendererCommand.SET_POSITION,
                            "latitude": latitude, "longitude": longitude})

    def fit_bounds(self, south: float, west: float, north: float, east: float,
                   padding: float = 40.0) -> None:
        self._send_command({"command": MapRendererCommand.FIT_BOUNDS,
                            "south": south, "west": west, "north": north,
                            "east": east, "padding": padding})

    def _send_command(self, command: dict[str, object]) -> None:
        context = zmq.Context()
        client = context.socket(zmq.REQ)
        client.setsockopt(zmq.LINGER, 0)
        client.setsockopt(zmq.SNDTIMEO, self._timeout_ms)
        client.setsockopt(zmq.RCVTIMEO, self._timeout_ms)

        try:
            client.connect(self._endpoint)
            client.send_string(json.dumps(command))
            response = client.recv_json()
        except (zmq.Again, zmq.ZMQError, ValueError) as exc:
            raise MapRendererUnavailableError(
                f"Map renderer unavailable at {self._endpoint}"
            ) from exc
        finally:
            client.close(linger=0)
            context.term()

        if not isinstance(response, dict) or not response.get("ok", False):
            message = (
                response.get("message", "Map renderer rejected command")
                if isinstance(response, dict)
                else "Invalid map renderer response"
            )
            raise MapRendererCommandError(str(message))
