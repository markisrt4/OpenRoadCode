# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Encode and decode vehicle-frame IMU telemetry."""

from collections.abc import Mapping
from typing import Any

from messaging.contracts.common.timestamp import decode_timestamp, validate_timestamp

from .imu_state_message import ImuStateData, ImuStateMessage, Vector3Data
from .imu_state_validator import SCHEMA_VERSION, validate_imu_state


def _vector_payload(vector: Mapping[str, float]) -> dict[str, float]:
    return {axis: vector[axis] for axis in ("x", "y", "z")}


def encode_imu_state(
    *,
    timestamp: Mapping[str, int],
    source: str,
    acceleration_m_s2: Mapping[str, float],
    linear_acceleration_m_s2: Mapping[str, float],
    angular_velocity_rad_s: Mapping[str, float],
) -> dict[str, Any]:
    validate_timestamp(timestamp)
    payload = {
        "version": SCHEMA_VERSION,
        "timestamp": dict(timestamp),
        "source": source,
        "data": {
            "acceleration_m_s2": _vector_payload(acceleration_m_s2),
            "linear_acceleration_m_s2": _vector_payload(linear_acceleration_m_s2),
            "angular_velocity_rad_s": _vector_payload(angular_velocity_rad_s),
        },
    }
    validate_imu_state(payload)
    return payload


def decode_imu_state(payload: Mapping[str, Any]) -> ImuStateMessage:
    validate_imu_state(payload)
    data = payload["data"]
    return ImuStateMessage(
        version=payload["version"],
        timestamp=decode_timestamp(payload["timestamp"]),
        source=payload["source"],
        data=ImuStateData(
            acceleration_m_s2=Vector3Data(**data["acceleration_m_s2"]),
            linear_acceleration_m_s2=Vector3Data(**data["linear_acceleration_m_s2"]),
            angular_velocity_rad_s=Vector3Data(**data["angular_velocity_rad_s"]),
        ),
    )
