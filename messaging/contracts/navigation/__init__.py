# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Public navigation message contracts.

The package initializer intentionally avoids importing codec modules. Some
producer-side codecs accept controller state objects, and eagerly importing
those modules would make an unrelated consumer (for example an IMU subscriber)
load controller, application, and optional platform dependencies.

Import codecs from their concrete modules, e.g.::

    from messaging.contracts.navigation.imu_state_codec import decode_imu_state
"""

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

__all__ = [
    "ATTITUDE_STATE_TOPIC", "AttitudeStateData", "AttitudeStateMessage",
    "IMU_STATE_TOPIC", "ImuStateData", "ImuStateMessage", "Vector3Data",
    "MOTION_STATE_TOPIC", "MotionStateData", "MotionStateMessage",
    "POSITION_STATE_TOPIC", "PositionStateData", "PositionStateMessage",
]
