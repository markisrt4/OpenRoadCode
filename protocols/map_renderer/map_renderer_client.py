# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Client for publishing native map-renderer commands on the ORC message bus."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from messaging.publisher_if import PublisherIf
from messaging.zeromq.publisher import ZeroMqPublisher

from .map_renderer_protocol import MAP_RENDERER_COMMAND_TOPIC, MapRendererCommand


class MapRendererUnavailableError(RuntimeError):
    """Raised when a map-renderer command cannot be published."""


class MapRendererCommandError(RuntimeError):
    """Retained for compatibility with callers of the former request/reply client."""


class MapRendererClient:
    """Publish asynchronous map-renderer commands through the ORC broker.

    The publisher is created eagerly and used directly by the UI thread. ZeroMQ
    PUB sends are non-blocking for this local in-process command path, so an
    extra Python queue/sender thread only adds scheduling latency to interactive
    camera controls and can accumulate stale camera commands.
    """

    def __init__(self, publisher: PublisherIf | None = None, *, endpoint: str | None = None,
                 timeout_ms: int | None = None) -> None:
        del timeout_ms
        self._publisher = publisher or (ZeroMqPublisher(endpoint) if endpoint else ZeroMqPublisher())
        self._owns_publisher = publisher is None
        self._closed = False
        self._send_error: Exception | None = None

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._owns_publisher:
            self._publisher.close()

    def set_camera(self, latitude: float, longitude: float, zoom: float,
                   bearing: float = 0.0, pitch: float = 0.0) -> None:
        self._send_command({"command": MapRendererCommand.SET_CAMERA,
            "latitude": latitude, "longitude": longitude, "zoom": zoom,
            "bearing": bearing, "pitch": pitch})

    def set_route(self, geojson: dict[str, object]) -> None:
        self._send_command({"command": MapRendererCommand.SET_ROUTE, "geojson": geojson})

    def set_center(self, latitude: float, longitude: float) -> None:
        self._send_command({"command": MapRendererCommand.SET_CENTER,
            "latitude": latitude, "longitude": longitude})

    def set_position(self, latitude: float, longitude: float) -> None:
        self._send_command({"command": MapRendererCommand.SET_POSITION,
            "latitude": latitude, "longitude": longitude})

    def set_poi_focus(self, category: str | None, enabled: bool = True) -> None:
        self._send_command({"command": MapRendererCommand.SET_POI_FOCUS,
            "category": category or "", "enabled": enabled if category else False})

    def fit_bounds(self, south: float, west: float, north: float, east: float,
                   padding: float = 40.0) -> None:
        self._send_command({"command": MapRendererCommand.FIT_BOUNDS,
            "south": south, "west": west, "north": north, "east": east,
            "padding": padding})

    def fit_dataset(self, padding: float = 24.0) -> None:
        """Frame the installed offline map dataset."""
        self._send_command({"command": MapRendererCommand.FIT_DATASET, "padding": padding})

    def _send_command(self, command: Mapping[str, Any]) -> None:
        if self._closed:
            raise MapRendererUnavailableError("map renderer client is closed")
        if self._send_error is not None:
            raise MapRendererUnavailableError("unable to publish map renderer command") from self._send_error
        try:
            self._publisher.publish(MAP_RENDERER_COMMAND_TOPIC, command)
        except (RuntimeError, OSError) as exc:
            self._send_error = exc
            raise MapRendererUnavailableError("unable to publish map renderer command") from exc
