# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Runtime adapters used by the ORC Tk shell.

The shell consumes these semantic adapters instead of constructing process,
ZeroMQ, decoder, or presenter infrastructure itself.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Protocol

from apps.launchers.map_renderer_launcher import MapRendererLauncher
from apps.orcUi.navigation_presenter import (
    AttitudePresentationState,
    NavigationPresenter,
    PositionPresentationState,
)
from apps.orcUi.vehicle_presenter import VehiclePresenter, VehiclePresentationState
from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, decode_vehicle_state
from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    decode_attitude_state,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT


class MapRuntimeIf(Protocol):
    """Map-process behavior required by the Tk shell."""

    def launch(self, parent_window_id: int) -> None: ...

    def stop(self) -> None: ...


class MapRuntime:
    """Own the external map-renderer process and X11 launch details."""

    def __init__(self, renderer: MapRendererLauncher | None = None) -> None:
        self._renderer = renderer or MapRendererLauncher()

    def launch(self, parent_window_id: int) -> None:
        self._renderer.launch(
            display=os.environ.get("DISPLAY", ":1"),
            parent_window_id=parent_window_id,
        )

    def stop(self) -> None:
        self._renderer.stop()


class StateIngressRuntime:
    """Decode transport messages, present them, and dispatch UI-ready state."""

    def __init__(
        self,
        *,
        schedule_ui: Callable[[int, Callable[[], None]], object],
        apply_vehicle_state: Callable[[VehiclePresentationState], None],
        apply_position_state: Callable[[PositionPresentationState], None],
        apply_attitude_state: Callable[[AttitudePresentationState], None],
        dispatcher: MessageDispatcher | None = None,
    ) -> None:
        self._schedule_ui = schedule_ui
        self._apply_vehicle_state = apply_vehicle_state
        self._apply_position_state = apply_position_state
        self._apply_attitude_state = apply_attitude_state
        self._dispatcher = dispatcher or MessageDispatcher(
            ZeroMqSubscriber(LOCAL_SUBSCRIBER_ENDPOINT),
            error_handler=self._on_bus_error,
        )
        self._dispatcher.register(
            VEHICLE_STATE_TOPIC,
            decode_vehicle_state,
            self._on_vehicle_message,
        )
        self._dispatcher.register(
            POSITION_STATE_TOPIC,
            decode_position_state,
            self._on_position_message,
        )
        self._dispatcher.register(
            ATTITUDE_STATE_TOPIC,
            decode_attitude_state,
            self._on_attitude_message,
        )

    def start(self) -> None:
        self._dispatcher.start()

    def close(self) -> None:
        self._dispatcher.close()

    def _on_vehicle_message(self, message) -> None:
        state = VehiclePresenter.present(message.data)
        self._schedule_ui(0, lambda: self._apply_vehicle_state(state))

    def _on_position_message(self, message) -> None:
        state = NavigationPresenter.present_position(message.data)
        self._schedule_ui(0, lambda: self._apply_position_state(state))

    def _on_attitude_message(self, message) -> None:
        state = NavigationPresenter.present_attitude(message.data)
        self._schedule_ui(0, lambda: self._apply_attitude_state(state))

    @staticmethod
    def _on_bus_error(topic, error: Exception) -> None:
        print(f"WARNING: {topic}: {type(error).__name__}: {error}")
