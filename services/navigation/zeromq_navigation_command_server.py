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

    def __init__(self, service: NavigationCommandService, endpoint: str = DEFAULT_NAVIGATION_COMMAND_ENDPOINT) -> None:
        self._service = service
        self._endpoint = endpoint
        self._stop_event = Event()
        self._running = Event()
        self._context: zmq.Context | None = None
        self._socket: zmq.Socket | None = None

    @property
    def endpoint(self) -> str:
        return self._endpoint

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    def bind(self) -> None:
        """Bind before the worker starts so address errors reach startup code."""
        if self._socket is not None:
            return
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, 100)
        try:
            socket.bind(self._endpoint)
        except Exception:
            socket.close(linger=0)
            context.term()
            raise
        self._context = context
        self._socket = socket
        self._running.set()

    def run(self) -> None:
        socket = self._socket
        if socket is None:
            raise RuntimeError("navigation command server is not bound")
        try:
            while not self._stop_event.is_set():
                try:
                    request = socket.recv_json()
                except zmq.Again:
                    continue
                socket.send_json(self._handle_request(request))
        finally:
            self._release()

    def close(self) -> None:
        self._stop_event.set()
        if not self._running.is_set():
            self._release()

    def _release(self) -> None:
        socket, context = self._socket, self._context
        self._socket = None
        self._context = None
        self._running.clear()
        if socket is not None:
            socket.close(linger=0)
        if context is not None:
            context.term()

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
            return {"ok": False, "message": f"{type(error).__name__}: {error}"}
        return {"ok": result.ok, "message": result.message}
