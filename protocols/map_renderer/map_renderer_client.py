# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Client for controlling the native OpenRoadCode map renderer."""

from __future__ import annotations

import json
import socket
from pathlib import Path

from .map_renderer_protocol import MapRendererCommand


class MapRendererUnavailableError(RuntimeError):
    """Raised when the native map renderer is unavailable."""


class MapRendererClient:
    """Send commands to the native map renderer."""

    def __init__(
        self,
        socket_path: str | Path = "/tmp/openroadcode-map-renderer.sock",
    ) -> None:
        self._socket_path = Path(socket_path)

    def set_camera(
        self,
        latitude: float,
        longitude: float,
        zoom: float,
        bearing: float = 0.0,
        pitch: float = 0.0,
    ) -> None:
        """Set the complete map camera state."""

        self._send_command(
            {
                "command": MapRendererCommand.SET_CAMERA,
                "latitude": latitude,
                "longitude": longitude,
                "zoom": zoom,
                "bearing": bearing,
                "pitch": pitch,
            }
        )

    def set_route(
        self,
        geojson: dict[str, object],
    ) -> None:
        """Set the route displayed by the map renderer."""

        self._send_command(
            {
                "command": MapRendererCommand.SET_ROUTE,
                "geojson": geojson,
            }
        )

    def set_center(
        self,
        latitude: float,
        longitude: float,
    ) -> None:
        """Set the center of the displayed map."""

        self._send_command(
            {
                "command": MapRendererCommand.SET_CENTER,
                "latitude": latitude,
                "longitude": longitude,
            }
        )

    def set_position(
        self,
        latitude: float,
        longitude: float,
    ) -> None:
        """Set the current vehicle position."""

        self._send_command(
            {
                "command": MapRendererCommand.SET_POSITION,
                "latitude": latitude,
                "longitude": longitude,
            }
        )

    def fit_bounds(
        self,
        south: float,
        west: float,
        north: float,
        east: float,
        padding: float = 40.0,
    ) -> None:
        """Fit the map camera to geographic bounds."""

        self._send_command(
            {
                "command": MapRendererCommand.FIT_BOUNDS,
                "south": south,
                "west": west,
                "north": north,
                "east": east,
                "padding": padding,
            }
        )

    def _send_command(
        self,
        command: dict[str, object],
    ) -> None:
        payload = json.dumps(command) + "\n"

        try:
            with socket.socket(
                socket.AF_UNIX,
                socket.SOCK_STREAM,
            ) as client:
                client.connect(str(self._socket_path))
                client.sendall(payload.encode("utf-8"))

        except (FileNotFoundError, ConnectionRefusedError, OSError) as exc:
            raise MapRendererUnavailableError(
                f"Map renderer unavailable at {self._socket_path}"
            ) from exc
