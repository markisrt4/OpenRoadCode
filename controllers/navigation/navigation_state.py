"""Navigation controller state types."""

from dataclasses import dataclass, field
from datetime import datetime

from hardware_io.imu import Vector3


@dataclass(frozen=True, slots=True)
class GpsState:
    """Represent the latest normalized GPS report."""

    received_at: datetime = field(default_factory=datetime.now)
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    altitude_m: float | None = None
    speed_mps: float | None = None
    course_deg: float | None = None
    fix_mode: int | None = None
    satellites_visible: int | None = None
    satellites_used: int | None = None

    @property
    def has_fix(self) -> bool:
        """Return whether the GPS state contains a positional fix.

        @retval True Latitude and longitude are available.
        @retval False The state has no usable position.
        """
        return self.fix_mode is not None and self.fix_mode >= 2


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
    gps: GpsState | None = None
