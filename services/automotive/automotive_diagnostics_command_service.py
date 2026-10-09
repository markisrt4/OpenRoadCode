# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Service-owned command boundary for semantic vehicle diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from controllers.automotive.obd2 import Obd2DiagnosticsSnapshot

SCAN_DIAGNOSTICS_COMMAND = "scan_diagnostics"


@dataclass(frozen=True, slots=True)
class AutomotiveCommandResult:
    """Result returned through the automotive command transport."""

    ok: bool
    message: str
    data: Mapping[str, Any] | None = None


class AutomotiveDiagnosticsCommandService:
    """Run read-only diagnostics through the service-owned OBD manager."""

    def __init__(self, diagnostics_source: object | None) -> None:
        self._diagnostics_source = diagnostics_source

    def execute(
        self, command: str, arguments: Mapping[str, Any] | None = None
    ) -> AutomotiveCommandResult:
        del arguments
        if command != SCAN_DIAGNOSTICS_COMMAND:
            return AutomotiveCommandResult(False, f"Unknown automotive command: {command}")
        scanner = getattr(self._diagnostics_source, "scan_diagnostics", None)
        if not callable(scanner):
            return AutomotiveCommandResult(False, "OBD diagnostics are not available")
        snapshot = scanner()
        return AutomotiveCommandResult(
            True,
            "Vehicle diagnostic scan complete",
            self._encode_snapshot(snapshot),
        )

    @staticmethod
    def _encode_snapshot(snapshot: Obd2DiagnosticsSnapshot) -> dict[str, Any]:
        return {
            "mil_on": snapshot.mil_on,
            "stored_dtc_count": snapshot.stored_dtc_count,
            "emissions_ready": snapshot.emissions_ready,
            "responding_ecus": list(snapshot.responding_ecus),
            "trouble_codes": [
                {
                    "code": item.code,
                    "status": item.status.name,
                    "ecu_id": item.ecu_id,
                }
                for item in snapshot.trouble_codes
            ],
        }
