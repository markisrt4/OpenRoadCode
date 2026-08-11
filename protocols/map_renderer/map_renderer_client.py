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
