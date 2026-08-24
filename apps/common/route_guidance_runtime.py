# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared composition for deriving route guidance from navigation positions."""

from __future__ import annotations

import math

from controllers.route_guidance import RouteGuidanceController
from controllers.route_planning.route_planning_types import GeoPoint
from messaging.contracts.navigation import (
    POSITION_STATE_TOPIC,
    PositionStateMessage,
    decode_position_state,
)
from messaging.contracts.route_guidance import RouteGuidanceStatePublisher
from messaging.message_dispatcher import MessageDispatcher
from messaging.subscriber_if import SubscriberIf


class RouteGuidanceRuntime:
    """Consume position messages and publish route-guidance state."""

    def __init__(
        self,
        subscriber: SubscriberIf,
        controller: RouteGuidanceController,
        publisher: RouteGuidanceStatePublisher,
    ) -> None:
        self._controller = controller
        self._publisher = publisher
        self._dispatcher = MessageDispatcher(subscriber)
        self._dispatcher.register(
            POSITION_STATE_TOPIC,
            decode_position_state,
            self._handle_position,
        )

    def start(self) -> None:
        """Start consuming navigation position messages."""
        self._dispatcher.start()

    def close(self) -> None:
        """Stop consuming navigation position messages."""
        self._dispatcher.close()

    def _handle_position(self, message: PositionStateMessage) -> None:
        data = message.data
        if data.latitude_rad is None or data.longitude_rad is None:
            return

        state = self._controller.update(
            GeoPoint(
                latitude=math.degrees(data.latitude_rad),
                longitude=math.degrees(data.longitude_rad),
            )
        )
        self._publisher.publish(state)
