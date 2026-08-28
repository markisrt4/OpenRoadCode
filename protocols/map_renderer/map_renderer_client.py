# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Client for publishing native map-renderer commands on the ORC message bus."""

from __future__ import annotations

from messaging.publisher_if import PublisherIf
from messaging.zeromq.publisher import ZeroMqPublisher

from .map_renderer_protocol import MAP_RENDERER_COMMAND_TOPIC, MapRendererCommand


class MapRendererUnavailableError(RuntimeError):
    """Raised when a map-renderer command cannot be published."""


class MapRendererCommandError(RuntimeError):
    """Retained for compatibility with callers of the former request/reply client."""


class MapRendererClient:
    """Publish asynchronous map-renderer commands through the ORC broker."""

    def __init__(
        self,
        publisher: PublisherIf | None = None,
        *,
        endpoint: str | None = None,
        timeout_ms: int | None = None,
    ) -> None:
        # endpoint and timeout_ms are accepted temporarily so older composition
        # code fails gracefully while the renderer transport moves to PUB/SUB.
        del timeout_ms
        self._publisher = publisher or ZeroMqPublisher(endpoint) if endpoint else (
            publisher or ZeroMqPublisher()
        )
        self._closed = False

    def close(self) -> None:
        """Close the command publisher."""
        if self._closed:
            return
        self._publisher.close()
        self._closed = True

    def set_camera(
        self,
        latitude: float,
        longitude: float,
        zoom: float,
        bearing: float = 0.0,
        pitch: float = 0.0,
    ) -> None:
        self._send_command({
            "command": MapRendererCommand.SET_CAMERA,
            "latitude": latitude,
            "longitude": longitude,
            "zoom": zoom,
            "bearing": bearing,
            "pitch": pitch,
        })

    def set_route(self, geojson: dict[str, object]) -> None:
        self._send_command({
            "command": MapRendererCommand.SET_ROUTE,
            "geojson": geojson,
        })

    def set_center(self, latitude: float, longitude: float) -> None:
        self._send_command({
            "command": MapRendererCommand.SET_CENTER,
            "latitude": latitude,
            "longitude": longitude,
        })

    def set_position(self, latitude: float, longitude: float) -> None:
        self._send_command({
            "command": MapRendererCommand.SET_POSITION,
            "latitude": latitude,
            "longitude": longitude,
        })

    def fit_bounds(
        self,
        south: float,
        west: float,
        north: float,
        east: float,
        padding: float = 40.0,
    ) -> None:
        self._send_command({
            "command": MapRendererCommand.FIT_BOUNDS,
            "south": south,
            "west": west,
            "north": north,
            "east": east,
            "padding": padding,
        })

    def _send_command(self, command: dict[str, object]) -> None:
        if self._closed:
            raise MapRendererUnavailableError("map renderer client is closed")
        try:
            self._publisher.publish(MAP_RENDERER_COMMAND_TOPIC, command)
        except (RuntimeError, OSError) as exc:
            raise MapRendererUnavailableError(
                "unable to publish map renderer command"
            ) from exc
