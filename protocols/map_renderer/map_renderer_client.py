# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Client for controlling the native OpenRoadCode map renderer."""

from __future__ import annotations

import json
import threading

import zmq

from .map_renderer_protocol import MapRendererCommand

DEFAULT_MAP_RENDERER_ENDPOINT = "ipc:///tmp/openroadcode-map-renderer"


class MapRendererUnavailableError(RuntimeError):
    """Raised when the native map renderer is unavailable."""


class MapRendererCommandError(RuntimeError):
    """Raised when the native map renderer rejects a command."""


class MapRendererClient:
    """Send request/reply commands to the native map renderer.

    The client keeps one ZeroMQ context and REQ socket alive across commands.
    Navigation follow mode can issue position and camera updates many times per
    second, so rebuilding the complete ZeroMQ transport for every command adds
    unnecessary latency and allocator/socket churn, especially on Termux.
    """

    def __init__(
        self,
        endpoint: str = DEFAULT_MAP_RENDERER_ENDPOINT,
        *,
        timeout_ms: int = 1000,
    ) -> None:
        self._endpoint = endpoint
        self._timeout_ms = timeout_ms
        self._context = zmq.Context()
        self._socket: zmq.Socket | None = None
        self._lock = threading.Lock()

    def close(self) -> None:
        """Close the renderer transport."""
        with self._lock:
            self._close_socket()
            if not self._context.closed:
                self._context.term()

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

    def _create_socket(self) -> zmq.Socket:
        socket = self._context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.SNDTIMEO, self._timeout_ms)
        socket.setsockopt(zmq.RCVTIMEO, self._timeout_ms)
        socket.connect(self._endpoint)
        return socket

    def _get_socket(self) -> zmq.Socket:
        if self._context.closed:
            raise MapRendererUnavailableError("Map renderer client is closed")
        if self._socket is None:
            self._socket = self._create_socket()
        return self._socket

    def _close_socket(self) -> None:
        if self._socket is not None:
            self._socket.close(linger=0)
            self._socket = None

    def _send_command(self, command: dict[str, object]) -> None:
        with self._lock:
            try:
                client = self._get_socket()
                client.send_string(json.dumps(command))
                response = client.recv_json()
            except (zmq.Again, zmq.ZMQError, ValueError) as exc:
                # A REQ socket cannot safely continue after a timed-out or
                # otherwise interrupted request/reply exchange. Recreate only
                # the socket so the next frame can recover without rebuilding
                # the entire ZeroMQ context.
                self._close_socket()
                raise MapRendererUnavailableError(
                    f"Map renderer unavailable at {self._endpoint}"
                ) from exc

        if not isinstance(response, dict) or not response.get("ok", False):
            message = (
                response.get("message", "Map renderer rejected command")
                if isinstance(response, dict)
                else "Invalid map renderer response"
            )
            raise MapRendererCommandError(str(message))
