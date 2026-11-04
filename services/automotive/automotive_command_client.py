# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Automotive command client; each call owns its socket, including after timeout."""
import zmq
from services.automotive.automotive_command_service import SCAN_DIAGNOSTICS_COMMAND, DIAGNOSTICS_STATUS_COMMAND
from services.automotive.endpoints import DEFAULT_AUTOMOTIVE_COMMAND_ENDPOINT

class AutomotiveCommandError(RuntimeError):
    pass

class AutomotiveCommandClient:
    def __init__(self, endpoint=DEFAULT_AUTOMOTIVE_COMMAND_ENDPOINT, *, timeout_ms=12000):
        self._endpoint = endpoint
        self._timeout_ms = timeout_ms

    def scan_diagnostics(self):
        return self._request(SCAN_DIAGNOSTICS_COMMAND, self._timeout_ms)

    def diagnostics_available(self):
        """Query service-owned connection state without opening or probing the adapter."""
        return self._request(DIAGNOSTICS_STATUS_COMMAND, 800).get("available") is True

    def _request(self, command, timeout_ms):
        with zmq.Context() as context:
            with context.socket(zmq.REQ) as socket:
                socket.setsockopt(zmq.LINGER, 0)
                socket.setsockopt(zmq.RCVTIMEO, timeout_ms)
                socket.setsockopt(zmq.SNDTIMEO, timeout_ms)
                socket.connect(self._endpoint)
                try:
                    socket.send_json({"command": command, "arguments": {}})
                    response = socket.recv_json()
                except zmq.Again as exc:
                    raise AutomotiveCommandError("Automotive command timed out") from exc
        if not isinstance(response, dict):
            raise AutomotiveCommandError("Invalid diagnostic response")
        if not response.get("ok"):
            raise AutomotiveCommandError(str(response.get("message", "Diagnostic scan failed")))
        if not isinstance(response.get("data"), dict):
            raise AutomotiveCommandError("Invalid diagnostic data")
        return response["data"]

    def close(self):
        pass
