# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Thread-safe attitude and IMU state consumed by the Car TUI."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from messaging.contracts.navigation import AttitudeStateMessage, ImuStateMessage
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
    attitude_source: str | None
    imu_source: str | None
    attitude_count: int
    imu_count: int
    error: str | None
    gps: object | None = None

    @property
    def connected(self) -> bool:
        return self.error is None and self.attitude_count > 0 and self.imu_count > 0

    @property
    def status(self) -> str:
        if self.error is not None:
            return self.error
        if not self.connected:
            return "Waiting for navigation telemetry"
        return f"Live navigation data · attitude {self.attitude_count} · IMU {self.imu_count}"


class NavigationBusState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._timestamp: datetime | None = None
        self._heading_deg: float | None = None
        self._pitch_deg: float | None = None
        self._roll_deg: float | None = None
        self._acceleration_mps2: Vector3Data | None = None
        self._linear_acceleration_mps2: Vector3Data | None = None
        self._angular_velocity_rad_s: Vector3Data | None = None
        self._attitude_source: str | None = None
        self._imu_source: str | None = None
        self._attitude_count = 0
        self._imu_count = 0
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
                attitude_source=self._attitude_source,
                imu_source=self._imu_source,
                attitude_count=self._attitude_count,
                imu_count=self._imu_count,
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
