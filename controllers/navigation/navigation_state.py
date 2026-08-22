# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Navigation controller state types."""

from dataclasses import dataclass, field
from datetime import datetime

from hardware_io.imu import Vector3


@dataclass(frozen=True, slots=True)
class PositionState:
    """Represent the latest normalized geographic position report."""

    received_at: datetime = field(default_factory=datetime.now)
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    altitude_m: float | None = None
    speed_mps: float | None = None
    course_deg: float | None = None
    vertical_speed_mps: float | None = None
    fix_mode: int | None = None
    satellites_visible: int | None = None
    satellites_used: int | None = None
    accuracy_m: float | None = None
    source: str = "unknown"
    is_cached: bool = False

    @property
    def has_fix(self) -> bool:
        """Return whether the position state contains a usable fix."""
        return self.fix_mode is not None and self.fix_mode >= 2


# Compatibility name for existing navigation consumers.
GpsState = PositionState


@dataclass(frozen=True, slots=True)
class OrientationState:
    """Represent a normalized orientation report from any orientation source."""

    received_at: datetime = field(default_factory=datetime.now)
    heading_deg: float | None = None
    pitch_deg: float | None = None
    roll_deg: float | None = None
    absolute: bool | None = None
    source: str = "unknown"


@dataclass(frozen=True, slots=True)
class NavigationState:
    """Represent one vehicle orientation and motion sample."""

    timestamp: datetime
    heading_deg: float
    pitch_deg: float
    roll_deg: float
    acceleration_mps2: Vector3
    linear_acceleration_mps2: Vector3
    angular_velocity_rad_s: Vector3
    gps: PositionState | None = None
