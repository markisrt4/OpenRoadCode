# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared composition for following navigation position and motion on the map."""

from __future__ import annotations

import math
from datetime import timedelta

from controllers.map_renderer.map_position_adapter import MapPositionAdapter
from controllers.navigation.navigation_state import GroundMotionState, PositionState
from messaging.contracts.common.timestamp import UNIX_EPOCH
from messaging.contracts.navigation import (
    MOTION_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    MotionStateMessage,
    PositionStateMessage,
    decode_motion_state,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.subscriber_if import SubscriberIf


def _received_at(message) -> object:
    return UNIX_EPOCH + timedelta(
        seconds=message.timestamp.seconds,
        microseconds=message.timestamp.nanoseconds / 1000.0,
    )


def position_message_to_state(message: PositionStateMessage) -> PositionState:
    """Convert the strict-SI position wire contract to controller state."""
    data = message.data
    return PositionState(
        received_at=_received_at(message),
        latitude_deg=None if data.latitude_rad is None else math.degrees(data.latitude_rad),
        longitude_deg=None if data.longitude_rad is None else math.degrees(data.longitude_rad),
        altitude_m=data.altitude_m,
        fix_mode=data.fix_mode,
        satellites_visible=data.satellites_visible,
        satellites_used=data.satellites_used,
        accuracy_m=data.accuracy_m,
        source=message.source,
        is_cached=data.is_cached,
    )


def motion_message_to_state(message: MotionStateMessage) -> GroundMotionState:
    """Convert the strict-SI motion wire contract to controller state."""
    data = message.data
    return GroundMotionState(
        received_at=_received_at(message),
        speed_mps=data.ground_speed_m_s,
        course_deg=None if data.course_rad is None else math.degrees(data.course_rad),
        source=message.source,
    )


class NavigationMapFollowRuntime:
    """Feed navigation position and motion messages into a MapPositionAdapter."""

    def __init__(self, subscriber: SubscriberIf, adapter: MapPositionAdapter) -> None:
        self._adapter = adapter
        self._dispatcher = MessageDispatcher(subscriber)
        self._dispatcher.register(
            POSITION_STATE_TOPIC,
            decode_position_state,
            self._handle_position,
        )
        self._dispatcher.register(
            MOTION_STATE_TOPIC,
            decode_motion_state,
            self._handle_motion,
        )

    def start(self) -> None:
        self._adapter.start()
        self._dispatcher.start()

    def close(self) -> None:
        self._dispatcher.close()
        self._adapter.stop()

    def _handle_position(self, message: PositionStateMessage) -> None:
        self._adapter.update(position_message_to_state(message))

    def _handle_motion(self, message: MotionStateMessage) -> None:
        self._adapter.update_ground_motion(motion_message_to_state(message))
