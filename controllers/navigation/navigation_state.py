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
    # Transitional in-process compatibility. Public position messages omit
    # motion; new callers should use GroundMotionState instead.
    speed_mps: float | None = None
    course_deg: float | None = None
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


@dataclass(frozen=True, slots=True)
class GroundMotionState:
    """Represent motion measured relative to the Earth's surface."""

    received_at: datetime = field(default_factory=datetime.now)
    speed_mps: float | None = None
    course_deg: float | None = None
    speed_accuracy_mps: float | None = None
    course_accuracy_deg: float | None = None
    source: str = "unknown"


# Compatibility name for existing navigation consumers while callers migrate
# from GPS-specific terminology to provider-neutral position terminology.
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
    """Represent one vehicle navigation solution sample."""

    timestamp: datetime
    heading_deg: float
    pitch_deg: float
    roll_deg: float
    acceleration_mps2: Vector3
    linear_acceleration_mps2: Vector3
    angular_velocity_rad_s: Vector3
    position: PositionState | None = None
    ground_motion: GroundMotionState | None = None

    @property
    def gps(self) -> PositionState | None:
        """Compatibility alias for legacy callers expecting ``state.gps``."""
        return self.position
