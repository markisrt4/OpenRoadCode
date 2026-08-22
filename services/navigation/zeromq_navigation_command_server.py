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
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REP)
        self._socket.setsockopt(zmq.LINGER, 0)
        self._socket.setsockopt(zmq.RCVTIMEO, 100)
        self._socket.bind(endpoint)

    @property
    def endpoint(self) -> str:
        """Return the endpoint bound by this server."""
        return self._endpoint

    def run(self) -> None:
        """Serve requests until close() is called."""
        while not self._stop_event.is_set():
            try:
                request = self._socket.recv_json()
            except zmq.Again:
                continue
            except zmq.ZMQError:
                if self._stop_event.is_set():
                    return
                raise

            response = self._handle_request(request)
            self._socket.send_json(response)

    def close(self) -> None:
        """Stop the service and release its ZeroMQ resources."""
        self._stop_event.set()
        self._socket.close(linger=0)
        self._context.term()

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
