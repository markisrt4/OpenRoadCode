# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import pytest

from controllers.navigation.imu_frame_normalizer import normalize_imu_to_vehicle
from messaging.contracts.common import Timestamp
from messaging.contracts.navigation.frames import (
    ANDROID_DEVICE_FRAME,
    VEHICLE_FRAME,
    WORLD_ENU_FRAME,
)
from messaging.contracts.navigation.imu_state_message import (
    ImuStateData,
    ImuStateMessage,
    Vector3Data,
)


def _message(frame_id: str) -> ImuStateMessage:
    return ImuStateMessage(
        version=1,
        timestamp=Timestamp(seconds=1, nanoseconds=2),
        source="test",
        frame_id=frame_id,
        data=ImuStateData(
            acceleration_m_s2=Vector3Data(1.0, 2.0, 3.0),
            linear_acceleration_m_s2=Vector3Data(4.0, 5.0, 6.0),
            angular_velocity_rad_s=Vector3Data(7.0, 8.0, 9.0),
        ),
    )


def test_vehicle_frame_passes_through() -> None:
    message = _message(VEHICLE_FRAME)

    assert normalize_imu_to_vehicle(message) is message


def test_android_frame_rotates_all_vectors_to_vehicle_frame() -> None:
    result = normalize_imu_to_vehicle(_message(ANDROID_DEVICE_FRAME))

    assert result.frame_id == VEHICLE_FRAME
    assert result.data.acceleration_m_s2 == Vector3Data(2.0, -1.0, 3.0)
    assert result.data.linear_acceleration_m_s2 == Vector3Data(5.0, -4.0, 6.0)
    assert result.data.angular_velocity_rad_s == Vector3Data(8.0, -7.0, 9.0)


def test_world_frame_is_rejected_without_orientation_transform() -> None:
    with pytest.raises(ValueError, match="cannot normalize IMU frame"):
        normalize_imu_to_vehicle(_message(WORLD_ENU_FRAME))
