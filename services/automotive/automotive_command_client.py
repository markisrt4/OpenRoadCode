# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Automotive command client; each call owns its socket, including after timeout."""
import zmq
from services.automotive.automotive_command_service import SCAN_DIAGNOSTICS_COMMAND
from services.automotive.endpoints import DEFAULT_AUTOMOTIVE_COMMAND_ENDPOINT

class AutomotiveCommandError(RuntimeError):
    pass

class AutomotiveCommandClient:
    def __init__(self, endpoint=DEFAULT_AUTOMOTIVE_COMMAND_ENDPOINT, *, timeout_ms=12000):
        self._endpoint = endpoint
        self._timeout_ms = timeout_ms

    def scan_diagnostics(self):
        with zmq.Context() as context:
            with context.socket(zmq.REQ) as socket:
                socket.setsockopt(zmq.LINGER, 0)
                socket.setsockopt(zmq.RCVTIMEO, self._timeout_ms)
                socket.setsockopt(zmq.SNDTIMEO, self._timeout_ms)
                socket.connect(self._endpoint)
                try:
                    socket.send_json({"command": SCAN_DIAGNOSTICS_COMMAND, "arguments": {}})
                    response = socket.recv_json()
                except zmq.Again as exc:
                    raise AutomotiveCommandError("Diagnostic scan timed out") from exc
        if not isinstance(response, dict):
            raise AutomotiveCommandError("Invalid diagnostic response")
        if not response.get("ok"):
            raise AutomotiveCommandError(str(response.get("message", "Diagnostic scan failed")))
        if not isinstance(response.get("data"), dict):
            raise AutomotiveCommandError("Invalid diagnostic data")
        return response["data"]

    def close(self):
        pass
