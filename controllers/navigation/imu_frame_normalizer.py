# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Normalize framed IMU telemetry into the OpenRoadCode vehicle frame."""

from __future__ import annotations

from messaging.contracts.navigation.frames import ANDROID_DEVICE_FRAME, VEHICLE_FRAME
from messaging.contracts.navigation.imu_state_message import (
    ImuStateData,
    ImuStateMessage,
    Vector3Data,
)


def normalize_imu_to_vehicle(message: ImuStateMessage) -> ImuStateMessage:
    """Return IMU telemetry expressed in the canonical ORC vehicle frame.

    Android device-frame vectors assume a portrait, screen-up phone with the
    top of the phone pointing toward the vehicle front. The ORC vehicle frame
    is right-handed: +X forward, +Y left, +Z up.
    """
    if message.frame_id == VEHICLE_FRAME:
        return message
    if message.frame_id != ANDROID_DEVICE_FRAME:
        raise ValueError(
            f"cannot normalize IMU frame {message.frame_id!r} to vehicle frame"
        )

    return ImuStateMessage(
        version=message.version,
        timestamp=message.timestamp,
        source=message.source,
        frame_id=VEHICLE_FRAME,
        data=ImuStateData(
            acceleration_m_s2=_android_to_vehicle(message.data.acceleration_m_s2),
            linear_acceleration_m_s2=_android_to_vehicle(
                message.data.linear_acceleration_m_s2
            ),
            angular_velocity_rad_s=_android_to_vehicle(
                message.data.angular_velocity_rad_s
            ),
        ),
    )


def _android_to_vehicle(vector: Vector3Data) -> Vector3Data:
    return Vector3Data(x=vector.y, y=-vector.x, z=vector.z)
