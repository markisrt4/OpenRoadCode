# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Typed client for service-owned vehicle diagnostic scans."""

from __future__ import annotations

from typing import Any

import zmq

from controllers.automotive.obd2 import (
    Obd2DiagnosticStatus,
    Obd2DiagnosticTroubleCode,
    Obd2DiagnosticsSnapshot,
)
from services.automotive.automotive_diagnostics_command_service import (
    SCAN_DIAGNOSTICS_COMMAND,
)
from services.automotive.endpoints import DEFAULT_AUTOMOTIVE_COMMAND_ENDPOINT


class AutomotiveDiagnosticsUnavailableError(RuntimeError):
    """Raised when the automotive command service cannot be reached."""


class AutomotiveDiagnosticsCommandError(RuntimeError):
    """Raised when the automotive service rejects a diagnostic command."""


class AutomotiveDiagnosticsClient:
    """Request typed diagnostic snapshots from the automotive service."""

    def __init__(
        self,
        endpoint: str = DEFAULT_AUTOMOTIVE_COMMAND_ENDPOINT,
        *,
        timeout_ms: int = 10_000,
    ) -> None:
        self._endpoint = endpoint
        self._timeout_ms = timeout_ms

    def scan(self) -> Obd2DiagnosticsSnapshot:
        response = self._request(SCAN_DIAGNOSTICS_COMMAND)
        data = response.get("data")
        if not isinstance(data, dict):
            raise AutomotiveDiagnosticsCommandError("Scan response contained no data")
        try:
            return Obd2DiagnosticsSnapshot(
                mil_on=data["mil_on"],
                stored_dtc_count=data["stored_dtc_count"],
                emissions_ready=data["emissions_ready"],
                responding_ecus=tuple(int(value) for value in data["responding_ecus"]),
                trouble_codes=tuple(
                    Obd2DiagnosticTroubleCode(
                        code=str(item["code"]),
                        status=Obd2DiagnosticStatus[str(item["status"])],
                        ecu_id=None if item["ecu_id"] is None else int(item["ecu_id"]),
                    )
                    for item in data["trouble_codes"]
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise AutomotiveDiagnosticsCommandError(
                f"Invalid diagnostic response: {exc}"
            ) from exc

    def _request(self, command: str) -> dict[str, Any]:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.SNDTIMEO, self._timeout_ms)
        socket.setsockopt(zmq.RCVTIMEO, self._timeout_ms)
        try:
            socket.connect(self._endpoint)
            socket.send_json({"command": command, "arguments": {}})
            response = socket.recv_json()
        except (zmq.Again, zmq.ZMQError, ValueError) as exc:
            raise AutomotiveDiagnosticsUnavailableError(
                f"Automotive diagnostics unavailable at {self._endpoint}"
            ) from exc
        finally:
            socket.close(linger=0)
            context.term()
        if not isinstance(response, dict):
            raise AutomotiveDiagnosticsCommandError("Invalid automotive response")
        if not response.get("ok", False):
            raise AutomotiveDiagnosticsCommandError(
                str(response.get("message", "Automotive diagnostic scan failed"))
            )
        return response
