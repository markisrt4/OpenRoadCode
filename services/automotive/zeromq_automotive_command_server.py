# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ZeroMQ request/reply server for automotive commands."""

from __future__ import annotations

from threading import Event
from typing import Any, Mapping

import zmq

from services.automotive.automotive_diagnostics_command_service import (
    AutomotiveDiagnosticsCommandService,
)
from services.automotive.endpoints import DEFAULT_AUTOMOTIVE_COMMAND_ENDPOINT


class ZeroMqAutomotiveCommandServer:
    """Serve automotive commands while retaining socket thread affinity."""

    def __init__(
        self,
        service: AutomotiveDiagnosticsCommandService,
        endpoint: str = DEFAULT_AUTOMOTIVE_COMMAND_ENDPOINT,
    ) -> None:
        self._service = service
        self._endpoint = endpoint
        self._stop_event = Event()
        self._running = Event()

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    def run(self) -> None:
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
                socket.send_json(self._handle_request(request))
        finally:
            self._running.clear()
            socket.close(linger=0)
            context.term()

    def close(self) -> None:
        self._stop_event.set()

    def _handle_request(self, request: Any) -> dict[str, Any]:
        if not isinstance(request, Mapping):
            return {"ok": False, "message": "Request must be a JSON object"}
        command = request.get("command")
        if not isinstance(command, str) or not command:
            return {"ok": False, "message": "Request command must be a string"}
        arguments = request.get("arguments", {})
        if not isinstance(arguments, Mapping):
            return {"ok": False, "message": "Request arguments must be an object"}
        try:
            result = self._service.execute(command, arguments)
        except Exception as exc:
            return {"ok": False, "message": f"{type(exc).__name__}: {exc}"}
        response: dict[str, Any] = {"ok": result.ok, "message": result.message}
        if result.data is not None:
            response["data"] = dict(result.data)
        return response
