# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Public navigation message contracts with lazy runtime helpers."""

from .attitude_state_message import AttitudeStateData, AttitudeStateMessage
from .imu_state_message import ImuStateData, ImuStateMessage, Vector3Data
from .motion_state_message import MotionStateData, MotionStateMessage
from .position_state_message import PositionStateData, PositionStateMessage
from .topics import (
    ATTITUDE_STATE_TOPIC,
    IMU_STATE_TOPIC,
    MOTION_STATE_TOPIC,
    POSITION_STATE_TOPIC,
)


def __getattr__(name: str):
    """Load codecs/publishers only when an application actually asks for them."""
    if name in {"encode_attitude_state", "decode_attitude_state", "validate_attitude_state"}:
        from .attitude_state_codec import decode_attitude_state, encode_attitude_state
        from .attitude_state_validator import validate_attitude_state
        return locals()[name]
    if name in {"encode_imu_state", "decode_imu_state", "validate_imu_state"}:
        from .imu_state_codec import decode_imu_state, encode_imu_state
        from .imu_state_validator import validate_imu_state
        return locals()[name]
    if name in {"encode_motion_state", "decode_motion_state", "validate_motion_state"}:
        from .motion_state_codec import decode_motion_state, encode_motion_state
        from .motion_state_validator import validate_motion_state
        return locals()[name]
    if name in {"encode_position_state", "decode_position_state", "validate_position_state"}:
        from .position_state_codec import decode_position_state, encode_position_state
        from .position_state_validator import validate_position_state
        return locals()[name]
    if name == "NavigationStatePublisher":
        from .navigation_state_publisher import NavigationStatePublisher
        return NavigationStatePublisher
    if name == "PositionStatePublisher":
        from .position_state_publisher import PositionStatePublisher
        return PositionStatePublisher
    raise AttributeError(name)


__all__ = [
    "ATTITUDE_STATE_TOPIC", "AttitudeStateData", "AttitudeStateMessage",
    "IMU_STATE_TOPIC", "ImuStateData", "ImuStateMessage", "Vector3Data",
    "MOTION_STATE_TOPIC", "MotionStateData", "MotionStateMessage",
    "POSITION_STATE_TOPIC", "PositionStateData", "PositionStateMessage",
    "encode_attitude_state", "decode_attitude_state", "validate_attitude_state",
    "encode_imu_state", "decode_imu_state", "validate_imu_state",
    "encode_motion_state", "decode_motion_state", "validate_motion_state",
    "encode_position_state", "decode_position_state", "validate_position_state",
    "NavigationStatePublisher", "PositionStatePublisher",
]
