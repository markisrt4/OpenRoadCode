# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Automotive diagnostic commands executed by the OBD-owning runtime."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

SCAN_DIAGNOSTICS_COMMAND = "automotive.diagnostics.scan"


class AutomotiveCommandService:
    """Execute commands against the automotive source owned by the runtime."""

    def __init__(self, source) -> None:
        self._source = source

    def execute(
        self,
        command: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        del arguments
        if command != SCAN_DIAGNOSTICS_COMMAND:
            return {"ok": False, "message": f"Unknown automotive command: {command}"}

        scanner = getattr(self._source, "scan_diagnostics", None)
        if not callable(scanner):
            return {"ok": False, "message": "Diagnostics are unavailable for this source"}

        snapshot = scanner()
        data = asdict(snapshot)
        data["trouble_codes"] = [
            {
                **item,
                "status": item["status"].name.lower(),
            }
            for item in data["trouble_codes"]
        ]
        return {
            "ok": True,
            "message": "Diagnostic scan complete",
            "data": data,
        }
