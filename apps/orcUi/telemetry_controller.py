# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Telemetry subscription and presentation for the ORC cockpit UI."""

from __future__ import annotations

from collections.abc import Callable

from apps.orcUi.navigation_presenter import (
    AttitudePresentationState,
    NavigationPresenter,
    PositionPresentationState,
)
from apps.orcUi.vehicle_presenter import VehiclePresenter, VehiclePresentationState
from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, VehicleStateMessage, decode_vehicle_state
from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    AttitudeStateMessage,
    PositionStateMessage,
    decode_attitude_state,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT


class TelemetryController:
    """Own the telemetry bus and emit frontend-ready presentation state."""

    def __init__(
        self,
        *,
        on_vehicle: Callable[[VehiclePresentationState], None],
        on_position: Callable[[PositionPresentationState], None],
        on_attitude: Callable[[AttitudePresentationState], None],
        on_error: Callable[[str, Exception], None] | None = None,
    ) -> None:
        self._on_vehicle = on_vehicle
        self._on_position = on_position
        self._on_attitude = on_attitude
        self._dispatcher = MessageDispatcher(
            ZeroMqSubscriber(LOCAL_SUBSCRIBER_ENDPOINT),
            error_handler=on_error or self._default_error_handler,
        )
        self._dispatcher.register(VEHICLE_STATE_TOPIC, decode_vehicle_state, self._handle_vehicle)
        self._dispatcher.register(POSITION_STATE_TOPIC, decode_position_state, self._handle_position)
        self._dispatcher.register(ATTITUDE_STATE_TOPIC, decode_attitude_state, self._handle_attitude)

    def start(self) -> None:
        self._dispatcher.start()

    def close(self) -> None:
        self._dispatcher.close()

    def _handle_vehicle(self, message: VehicleStateMessage) -> None:
        self._on_vehicle(VehiclePresenter.present(message.data))

    def _handle_position(self, message: PositionStateMessage) -> None:
        self._on_position(NavigationPresenter.present_position(message.data))

    def _handle_attitude(self, message: AttitudeStateMessage) -> None:
        self._on_attitude(NavigationPresenter.present_attitude(message.data))

    @staticmethod
    def _default_error_handler(topic: str, error: Exception) -> None:
        print(f"WARNING: {topic}: {type(error).__name__}: {error}")
