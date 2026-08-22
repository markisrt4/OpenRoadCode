# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Thread-safe cache for public navigation telemetry consumers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from controllers.navigation.navigation_state import PositionState
from messaging.contracts.navigation import (
    AttitudeStateMessage,
    ImuStateMessage,
    MotionStateMessage,
    PositionStateMessage,
)
from messaging.contracts.navigation.imu_state_message import Vector3Data


@dataclass(frozen=True, slots=True)
class NavigationBusSnapshot:
    timestamp: datetime | None
    heading_deg: float | None
    pitch_deg: float | None
    roll_deg: float | None
    acceleration_mps2: Vector3Data | None
    linear_acceleration_mps2: Vector3Data | None
    angular_velocity_rad_s: Vector3Data | None
    gps: PositionState | None
    ground_speed_m_s: float | None
    vertical_speed_m_s: float | None
    turn_rate_rad_s: float | None
    attitude_source: str | None
    imu_source: str | None
    position_source: str | None
    motion_source: str | None
    attitude_count: int
    imu_count: int
    position_count: int
    motion_count: int
    error: str | None

    @property
    def connected(self) -> bool:
        return self.error is None and self.attitude_count > 0 and self.imu_count > 0

    @property
    def status(self) -> str:
        if self.error is not None:
            return self.error
        if not self.connected:
            return "Waiting for navigation telemetry"
        suffix = ""
        if self.position_count or self.motion_count:
            suffix = f" · position {self.position_count} · motion {self.motion_count}"
        return (
            f"Live navigation data · attitude {self.attitude_count} · IMU {self.imu_count}"
            f"{suffix}"
        )


class NavigationBusState:
    """Collect navigation messages into one thread-safe latest-state snapshot."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._timestamp: datetime | None = None
        self._heading_deg: float | None = None
        self._pitch_deg: float | None = None
        self._roll_deg: float | None = None
        self._acceleration_mps2: Vector3Data | None = None
        self._linear_acceleration_mps2: Vector3Data | None = None
        self._angular_velocity_rad_s: Vector3Data | None = None
        self._gps: PositionState | None = None
        self._ground_speed_m_s: float | None = None
        self._vertical_speed_m_s: float | None = None
        self._turn_rate_rad_s: float | None = None
        self._attitude_source: str | None = None
        self._imu_source: str | None = None
        self._position_source: str | None = None
        self._motion_source: str | None = None
        self._attitude_count = 0
        self._imu_count = 0
        self._position_count = 0
        self._motion_count = 0
        self._error: str | None = None

    def set_attitude(self, message: AttitudeStateMessage) -> None:
        with self._lock:
            self._timestamp = _datetime(message)
            self._heading_deg = _degrees(message.data.heading_rad)
            self._pitch_deg = _degrees(message.data.pitch_rad)
            self._roll_deg = _degrees(message.data.roll_rad)
            self._attitude_source = message.source
            self._attitude_count += 1
            self._error = None

    def set_imu(self, message: ImuStateMessage) -> None:
        with self._lock:
            self._timestamp = _datetime(message)
            self._acceleration_mps2 = message.data.acceleration_m_s2
            self._linear_acceleration_mps2 = message.data.linear_acceleration_m_s2
            self._angular_velocity_rad_s = message.data.angular_velocity_rad_s
            self._imu_source = message.source
            self._imu_count += 1
            self._error = None

    def set_position(self, message: PositionStateMessage) -> None:
        data = message.data
        received_at = _datetime(message)
        gps = PositionState(
            received_at=received_at,
            latitude_deg=_degrees(data.latitude_rad),
            longitude_deg=_degrees(data.longitude_rad),
            altitude_m=data.altitude_m,
            speed_mps=data.speed_m_s,
            course_deg=_degrees(data.course_rad),
            fix_mode=data.fix_mode,
            satellites_visible=data.satellites_visible,
            satellites_used=data.satellites_used,
            accuracy_m=data.accuracy_m,
            source=message.source,
            is_cached=data.is_cached,
        )
        with self._lock:
            self._timestamp = received_at
            self._gps = gps
            self._position_source = message.source
            self._position_count += 1
            self._error = None

    def set_motion(self, message: MotionStateMessage) -> None:
        data = message.data
        with self._lock:
            self._timestamp = _datetime(message)
            self._ground_speed_m_s = data.ground_speed_m_s
            self._vertical_speed_m_s = data.vertical_speed_m_s
            self._turn_rate_rad_s = data.turn_rate_rad_s
            self._motion_source = message.source
            self._motion_count += 1
            self._error = None

    def set_error(self, topic: str, error: Exception) -> None:
        with self._lock:
            self._error = f"Navigation bus error [{topic}]: {type(error).__name__}: {error}"

    def snapshot(self) -> NavigationBusSnapshot:
        with self._lock:
            return NavigationBusSnapshot(
                timestamp=self._timestamp,
                heading_deg=self._heading_deg,
                pitch_deg=self._pitch_deg,
                roll_deg=self._roll_deg,
                acceleration_mps2=self._acceleration_mps2,
                linear_acceleration_mps2=self._linear_acceleration_mps2,
                angular_velocity_rad_s=self._angular_velocity_rad_s,
                gps=self._gps,
                ground_speed_m_s=self._ground_speed_m_s,
                vertical_speed_m_s=self._vertical_speed_m_s,
                turn_rate_rad_s=self._turn_rate_rad_s,
                attitude_source=self._attitude_source,
                imu_source=self._imu_source,
                position_source=self._position_source,
                motion_source=self._motion_source,
                attitude_count=self._attitude_count,
                imu_count=self._imu_count,
                position_count=self._position_count,
                motion_count=self._motion_count,
                error=self._error,
            )


def _degrees(value: float | None) -> float | None:
    return None if value is None else math.degrees(value)


def _datetime(message) -> datetime:
    timestamp = message.timestamp
    return datetime.fromtimestamp(
        timestamp.seconds + timestamp.nanoseconds / 1_000_000_000.0,
        tz=timezone.utc,
    )
