# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ZeroMQ transport for commands executed by AutomotiveRuntime."""

from __future__ import annotations

from concurrent.futures import TimeoutError as FutureTimeoutError
from threading import Event
import time
from typing import Any, Mapping

import zmq

from services.automotive.endpoints import DEFAULT_AUTOMOTIVE_COMMAND_ENDPOINT


class ZeroMqAutomotiveCommandServer:
    def __init__(self, runtime, endpoint: str = DEFAULT_AUTOMOTIVE_COMMAND_ENDPOINT) -> None:
        self.bound_endpoint: str | None = None
        self._runtime = runtime
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
        try:
            socket.bind(self._endpoint)
            self.bound_endpoint = socket.getsockopt(zmq.LAST_ENDPOINT).decode()
            self._running.set()
            while not self._stop_event.is_set():
                try:
                    request = socket.recv_json()
                except zmq.Again:
                    continue
                except ValueError:
                    socket.send_json({"ok": False, "message": "Request must be valid JSON"})
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
        arguments = request.get("arguments", {})
        if not isinstance(command, str) or not command:
            return {"ok": False, "message": "Request command must be a non-empty string"}
        if not isinstance(arguments, Mapping):
            return {"ok": False, "message": "Request arguments must be a JSON object"}
        future = self._runtime.request_command(command, arguments)
        deadline = time.monotonic() + 11.0
        while not self._stop_event.is_set():
            try:
                return future.result(timeout=0.1)
            except FutureTimeoutError:
                if time.monotonic() >= deadline:
                    future.cancel()
                    return {"ok": False, "message": f"Automotive command timed out: {command}"}
            except Exception as error:
                return {"ok": False, "message": f"{type(error).__name__}: {error}"}
        future.cancel()
        return {"ok": False, "message": "Automotive command server stopped"}
