# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Expose navigation ground speed as a partial automotive vehicle state."""

from __future__ import annotations

from datetime import datetime
from threading import Lock

from controllers.automotive.vehicle_state import VehicleState
from controllers.automotive.vehicle_state_source_if import VehicleStateSourceIf
from messaging.contracts.navigation import (
    MOTION_STATE_TOPIC,
    MotionStateMessage,
    decode_motion_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.subscriber_if import SubscriberIf


class NavigationMotionVehicleStateSource(VehicleStateSourceIf):
    """Build partial vehicle snapshots from navigation ground-motion messages.

    This source intentionally supplies only fields that navigation can measure
    directly.  Engine, fuel, temperature, pressure, and transmission fields
    remain ``None`` rather than being simulated.
    """

    def __init__(self, subscriber: SubscriberIf) -> None:
        self._lock = Lock()
        self._speed_m_s: float | None = None
        self._connected = False
        self._dispatcher = MessageDispatcher(subscriber)
        self._dispatcher.register(
            MOTION_STATE_TOPIC,
            decode_motion_state,
            self._on_motion_state,
        )

    def connect(self) -> None:
        """Start receiving navigation ground-motion telemetry."""
        if self._connected:
            return
        self._dispatcher.start()
        self._connected = True

    def disconnect(self) -> None:
        """Stop receiving navigation ground-motion telemetry."""
        if not self._connected:
            return
        self._dispatcher.close()
        self._connected = False

    def read_state(self) -> VehicleState:
        """Return a vehicle state containing the latest real GPS ground speed.

        @return Partial vehicle state with ``vehicle_speed_m_s`` populated when
        navigation has supplied a valid ground speed.
        """
        with self._lock:
            speed_m_s = self._speed_m_s
        return VehicleState(
            timestamp=datetime.now(),
            vehicle_speed_m_s=speed_m_s,
        )

    def _on_motion_state(self, message: MotionStateMessage) -> None:
        with self._lock:
            self._speed_m_s = message.data.ground_speed_m_s
