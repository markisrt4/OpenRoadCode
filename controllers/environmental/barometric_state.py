# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Barometric controller state types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class BarometricState:
    """Processed barometric measurements."""

    pressure_pa: float
    temperature_c: float
    altitude_m: float
    relative_altitude_m: float
    vertical_speed_mps: float
    timestamp: datetime

    @staticmethod
    def create(
        *,
        pressure_pa: float,
        temperature_c: float,
        altitude_m: float,
        relative_altitude_m: float,
        vertical_speed_mps: float,
    ) -> BarometricState:
        """Create a state using the current UTC timestamp."""

        return BarometricState(
            pressure_pa=pressure_pa,
            temperature_c=temperature_c,
            altitude_m=altitude_m,
            relative_altitude_m=relative_altitude_m,
            vertical_speed_mps=vertical_speed_mps,
            timestamp=datetime.now(timezone.utc),
        )
