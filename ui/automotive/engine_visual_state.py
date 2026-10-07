# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Measured update rates for an engine presentation surface."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EngineUpdateRates:
    """Actual vehicle snapshots and completed draws per elapsed second."""

    telemetry_hz: float = 0.0
    render_hz: float = 0.0
