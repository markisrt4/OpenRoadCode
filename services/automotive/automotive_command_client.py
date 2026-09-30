# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Client for acknowledged automotive commands."""

from __future__ import annotations

import zmq

from services.automotive.automotive_command_service import SCAN_DIAGNOSTICS_COMMAND
from services.automotive.endpoints import DEFAULT_AUTOMOTIVE_COMMAND_ENDPOINT


class AutomotiveCommandError(RuntimeError):
    pass


class AutomotiveCommandClient:
    def __init__(
        self,
        endpoint: str = DEFAULT_AUTOMOTIVE_COMMAND_ENDPOINT,
        *,
        timeout_ms: int = 12000,
    ) -> None:
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REQ)
        self._socket.setsockopt(zmq.LINGER, 0)
        self._socket.setsockopt(zmq.RCVTIMEO, timeout_ms)
        self._socket.setsockopt(zmq.SNDTIMEO, timeout_ms)
        self._socket.connect(endpoint)

    def scan_diagnostics(self) -> dict:
        try:
            self._socket.send_json({"command": SCAN_DIAGNOSTICS_COMMAND, "arguments": {}})
            response = self._socket.recv_json()
        except zmq.Again as error:
            raise AutomotiveCommandError("Diagnostic scan timed out") from error
        if not isinstance(response, dict) or not response.get("ok", False):
            message = response.get("message", "Diagnostic scan failed") if isinstance(response, dict) else "Invalid automotive command response"
            raise AutomotiveCommandError(str(message))
        data = response.get("data")
        if not isinstance(data, dict):
            raise AutomotiveCommandError("Diagnostic scan returned invalid data")
        return data

    def close(self) -> None:
        self._socket.close(linger=0)
        self._context.term()
