# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared composition for following navigation position messages on the map."""

from __future__ import annotations

import math
from datetime import timedelta

from controllers.map_renderer.map_position_adapter import MapPositionAdapter
from controllers.navigation.navigation_state import PositionState
from messaging.contracts.common.timestamp import UNIX_EPOCH
from messaging.contracts.navigation import (
    POSITION_STATE_TOPIC,
    PositionStateMessage,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.subscriber_if import SubscriberIf


def position_message_to_state(message: PositionStateMessage) -> PositionState:
    """Convert the strict-SI wire contract back to controller position state."""
    data = message.data
    received_at = UNIX_EPOCH + timedelta(
        seconds=message.timestamp.seconds,
        microseconds=message.timestamp.nanoseconds / 1000.0,
    )
    return PositionState(
        received_at=received_at,
        latitude_deg=(
            None if data.latitude_rad is None else math.degrees(data.latitude_rad)
        ),
        longitude_deg=(
            None if data.longitude_rad is None else math.degrees(data.longitude_rad)
        ),
        altitude_m=data.altitude_m,
        speed_mps=data.speed_m_s,
        course_deg=(
            None if data.course_rad is None else math.degrees(data.course_rad)
        ),
        fix_mode=data.fix_mode,
        satellites_visible=data.satellites_visible,
        satellites_used=data.satellites_used,
        accuracy_m=data.accuracy_m,
        source=message.source,
        is_cached=data.is_cached,
    )


class NavigationMapFollowRuntime:
    """Feed navigation position bus messages into a MapPositionAdapter."""

    def __init__(
        self,
        subscriber: SubscriberIf,
        adapter: MapPositionAdapter,
    ) -> None:
        self._adapter = adapter
        self._dispatcher = MessageDispatcher(subscriber)
        self._dispatcher.register(
            POSITION_STATE_TOPIC,
            decode_position_state,
            self._handle_position,
        )

    def start(self) -> None:
        """Start map interpolation and navigation message reception."""
        self._adapter.start()
        self._dispatcher.start()

    def close(self) -> None:
        """Stop message reception and map interpolation."""
        self._dispatcher.close()
        self._adapter.stop()

    def _handle_position(self, message: PositionStateMessage) -> None:
        self._adapter.update(position_message_to_state(message))
