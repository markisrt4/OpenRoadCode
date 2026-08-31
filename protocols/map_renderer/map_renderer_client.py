# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Client for publishing native map-renderer commands on the ORC message bus."""

from __future__ import annotations

from collections.abc import Mapping
from queue import Queue
from threading import Thread
from typing import Any

from messaging.publisher_if import PublisherIf
from messaging.zeromq.publisher import ZeroMqPublisher

from .map_renderer_protocol import MAP_RENDERER_COMMAND_TOPIC, MapRendererCommand


class MapRendererUnavailableError(RuntimeError):
    """Raised when a map-renderer command cannot be published."""


class MapRendererCommandError(RuntimeError):
    """Retained for compatibility with callers of the former request/reply client."""


_STOP = object()


class MapRendererClient:
    """Publish asynchronous map-renderer commands through the ORC broker.

    The default ZeroMQ publisher is created and used exclusively by one sender
    thread. ZeroMQ sockets are thread-affine, while ORC camera requests can
    originate from both UI callbacks and MessageDispatcher worker threads.
    Keeping transport ownership here lets callers use this client safely from
    either context without leaking ZeroMQ threading rules into UI code.
    """

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
        self._publisher = publisher
        self._endpoint = endpoint
        self._closed = False
        self._send_error: Exception | None = None
        self._queue: Queue[Mapping[str, Any] | object] | None = None
        self._sender_thread: Thread | None = None

        if publisher is None:
            self._queue = Queue()
            self._sender_thread = Thread(
                target=self._sender_loop,
                name="map-renderer-command-publisher",
                daemon=True,
            )
            self._sender_thread.start()

    def close(self) -> None:
        """Close renderer-command resources after draining queued commands."""
        if self._closed:
            return
        self._closed = True

        if self._queue is not None and self._sender_thread is not None:
            self._queue.put(_STOP)
            self._sender_thread.join(timeout=1.0)
            return

        if self._publisher is not None:
            self._publisher.close()

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
        if self._send_error is not None:
            raise MapRendererUnavailableError(
                "unable to publish map renderer command"
            ) from self._send_error

        if self._queue is not None:
            self._queue.put(command)
            return

        if self._publisher is None:
            raise MapRendererUnavailableError("map renderer publisher is unavailable")
        try:
            self._publisher.publish(MAP_RENDERER_COMMAND_TOPIC, command)
        except (RuntimeError, OSError) as exc:
            raise MapRendererUnavailableError(
                "unable to publish map renderer command"
            ) from exc

    def _sender_loop(self) -> None:
        publisher = ZeroMqPublisher(self._endpoint) if self._endpoint else ZeroMqPublisher()
        try:
            assert self._queue is not None
            while True:
                command = self._queue.get()
                try:
                    if command is _STOP:
                        return
                    publisher.publish(MAP_RENDERER_COMMAND_TOPIC, command)
                except Exception as exc:  # transport failure is reported on next request
                    self._send_error = exc
                finally:
                    self._queue.task_done()
        finally:
            publisher.close()
