# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Read-only diagnostic scan presentation and request contracts."""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DiagnosticFaultCard:
    """Driver-facing meaning and advice, retaining identifiers for technical views."""
    title: str
    reporting_status: str
    explanation: str
    recommendation: str
    code: str = ""
    ecu_id: int | None = None


@dataclass(frozen=True, slots=True)
class DiagnosticsScanState:
    scanning: bool = False
    status: str = "unavailable"
    summary: str = "Diagnostics have not been scanned."
    details: str = "Generic emissions diagnostics do not cover every vehicle system."
    faults: tuple[DiagnosticFaultCard, ...] = ()
    mil_on: bool | None = None
    emissions_ready: bool | None = None
    coverage_complete: bool = False
    coverage_message: str = "Run a scan to check available emissions diagnostics."
    next_action: str = "Park safely before reviewing diagnostic results."
    completed_at: datetime | None = None
    scan_available: bool = False
    connection_message: str = "Checking automotive connection…"


class DiagnosticsScanHandlerIf(Protocol):
    def request_scan(self) -> None: ...
    def observe(self, callback: Callable[[DiagnosticsScanState], None]) -> Callable[[], None]: ...
