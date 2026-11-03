# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Read-only diagnostic scan presentation and request contracts."""
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True, slots=True)
class DiagnosticsScanState:
    scanning: bool = False
    status: str = "unavailable"
    summary: str = "Diagnostics have not been scanned."
    details: str = "Generic emissions diagnostics do not cover every vehicle system."

class DiagnosticsScanHandlerIf(Protocol):
    def request_scan(self) -> None: ...
    def observe(self, callback: Callable[[DiagnosticsScanState], None]) -> Callable[[], None]: ...
