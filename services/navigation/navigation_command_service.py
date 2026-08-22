# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Navigation command service independent of its request transport."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from controllers.navigation.navigation_controller_if import NavigationControllerIf

CALIBRATE_STATIONARY_COMMAND = "navigation.calibrate_stationary"
RESET_HEADING_COMMAND = "navigation.reset_heading"


@dataclass(frozen=True, slots=True)
class NavigationCommandResult:
    """Result returned by one navigation command request."""

    ok: bool
    message: str


class NavigationCommandService:
    """Execute navigation commands against the telemetry-owning controller."""

    def __init__(self, controller: NavigationControllerIf) -> None:
        self._controller = controller

    def execute(
        self,
        command: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> NavigationCommandResult:
        """Execute one named command and return a transport-neutral result."""
        args = dict(arguments or {})

        if command == CALIBRATE_STATIONARY_COMMAND:
            sample_count = int(args.get("sample_count", 100))
            sample_interval_s = float(args.get("sample_interval_s", 0.01))
            self._controller.calibrate_stationary(
                sample_count=sample_count,
                sample_interval_s=sample_interval_s,
            )
            return NavigationCommandResult(True, "Stationary calibration complete")

        if command == RESET_HEADING_COMMAND:
            heading_deg = float(args.get("heading_deg", 0.0))
            self._controller.reset_heading(heading_deg)
            return NavigationCommandResult(True, "Heading reset complete")

        return NavigationCommandResult(False, f"Unknown navigation command: {command}")
