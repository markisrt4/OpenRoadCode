# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ZeroMQ request/reply transport for the navigation command service."""

from __future__ import annotations

from threading import Event
from typing import Any, Mapping

import zmq

from services.navigation.navigation_command_service import NavigationCommandService

DEFAULT_NAVIGATION_COMMAND_ENDPOINT = "tcp://127.0.0.1:5560"


class ZeroMqNavigationCommandServer:
    """Serve navigation commands over a small JSON REQ/REP protocol."""

    def __init__(
        self,
        service: NavigationCommandService,
        endpoint: str = DEFAULT_NAVIGATION_COMMAND_ENDPOINT,
    ) -> None:
        self._service = service
        self._endpoint = endpoint
        self._stop_event = Event()
        self._running = Event()

    @property
    def endpoint(self) -> str:
        """Return the endpoint bound by this server."""
        return self._endpoint

    @property
    def is_running(self) -> bool:
        """Return whether the command loop has created and bound its socket."""
        return self._running.is_set()

    def run(self) -> None:
        """Serve requests until close() is called.

        ZeroMQ sockets are thread-affine. Create, use, and close the REP socket
        entirely inside the server thread rather than closing it concurrently
        from the caller thread.
        """
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, 100)
        socket.bind(self._endpoint)
        self._running.set()
        try:
            while not self._stop_event.is_set():
                try:
                    request = socket.recv_json()
                except zmq.Again:
                    continue

                response = self._handle_request(request)
                socket.send_json(response)
        finally:
            self._running.clear()
            socket.close(linger=0)
            context.term()

    def close(self) -> None:
        """Request command-loop shutdown.

        The server thread observes this event through the short receive timeout
        and releases its own ZeroMQ resources. This avoids cross-thread socket
        destruction, which can abort libzmq on some platforms.
        """
        self._stop_event.set()

    def _handle_request(self, request: Any) -> dict[str, Any]:
        if not isinstance(request, Mapping):
            return {"ok": False, "message": "Request must be a JSON object"}

        command = request.get("command")
        if not isinstance(command, str) or not command:
            return {"ok": False, "message": "Request command must be a non-empty string"}

        arguments = request.get("arguments", {})
        if not isinstance(arguments, Mapping):
            return {"ok": False, "message": "Request arguments must be a JSON object"}

        try:
            result = self._service.execute(command, arguments)
        except Exception as error:
            return {
                "ok": False,
                "message": f"{type(error).__name__}: {error}",
            }

        return {"ok": result.ok, "message": result.message}
