# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Typed decoded representation of framed IMU telemetry."""

from dataclasses import dataclass

from messaging.contracts.common import Timestamp


@dataclass(frozen=True, slots=True)
class Vector3Data:
    x: float
    y: float
    z: float


@dataclass(frozen=True, slots=True)
class ImuStateData:
    acceleration_m_s2: Vector3Data
    linear_acceleration_m_s2: Vector3Data
    angular_velocity_rad_s: Vector3Data


@dataclass(frozen=True, slots=True)
class ImuStateMessage:
    version: int
    timestamp: Timestamp
    source: str
    frame_id: str
    data: ImuStateData
