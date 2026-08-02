"""Environmental controller state types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class EnvironmentalState:
    """Processed environmental measurements."""

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
    ) -> EnvironmentalState:
        """Create a state using the current UTC timestamp."""

        return EnvironmentalState(
            pressure_pa=pressure_pa,
            temperature_c=temperature_c,
            altitude_m=altitude_m,
            relative_altitude_m=relative_altitude_m,
            vertical_speed_mps=vertical_speed_mps,
            timestamp=datetime.now(timezone.utc),
        )
