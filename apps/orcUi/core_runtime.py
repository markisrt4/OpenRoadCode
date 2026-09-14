# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Runtime adapters used by the ORC Tk shell.

The shell consumes these semantic adapters instead of constructing process,
ZeroMQ, decoder, or presenter infrastructure itself.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from queue import Empty, SimpleQueue
from typing import Protocol

from apps.launchers.map_renderer_launcher import MapRendererLauncher
from apps.orcUi.map_theme_runtime import install_map_style
from apps.orcUi.navigation_presenter import (
    AttitudePresentationState,
    NavigationPresenter,
    PositionPresentationState,
)
from apps.orcUi.trip_presenter import TripPresenter, TripPresentationState
from apps.orcUi.vehicle_presenter import VehiclePresenter, VehiclePresentationState
from controllers.automotive import EngineAnalysis, EngineAnalyzer, VehicleConfiguration
from messaging.contracts.automotive import (
    TRIP_STATE_TOPIC,
    VEHICLE_STATE_TOPIC,
    decode_trip_state,
    decode_vehicle_state,
)
from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    decode_attitude_state,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT
from ui.theme import ThemeMode


class MapRuntimeIf(Protocol):
    """Map-process behavior required by the Tk shell."""

    def set_theme(self, mode: ThemeMode) -> None: ...

    def launch(self, parent_window_id: int) -> None: ...

    def stop(self) -> None: ...


class MapRuntime:
    """Own the external map-renderer process, style, and X11 launch details."""

    def __init__(self, renderer: MapRendererLauncher | None = None) -> None:
        self._renderer = renderer or MapRendererLauncher()

    def set_theme(self, mode: ThemeMode) -> None:
        """Install map presentation assets for the requested ORC theme."""
        install_map_style(mode)

    def launch(self, parent_window_id: int) -> None:
        self._renderer.launch(
            display=os.environ.get("DISPLAY", ":1"),
            parent_window_id=parent_window_id,
        )

    def stop(self) -> None:
        self._renderer.stop()


class StateIngressRuntime:
    """Decode transport messages, present them, and dispatch UI-ready state."""

    _UI_DRAIN_INTERVAL_MS = 16

    def __init__(
        self,
        *,
        schedule_ui: Callable[[int, Callable[[], None]], object],
        apply_vehicle_state: Callable[[VehiclePresentationState], None],
        apply_engine_analysis: Callable[[EngineAnalysis], None],
        apply_trip_state: Callable[[TripPresentationState], None],
        vehicle_configuration: VehicleConfiguration = VehicleConfiguration(),
        apply_position_state: Callable[[PositionPresentationState], None],
        apply_attitude_state: Callable[[AttitudePresentationState], None],
        dispatcher: MessageDispatcher | None = None,
    ) -> None:
        self._schedule_ui = schedule_ui
        self._apply_vehicle_state = apply_vehicle_state
        self._apply_engine_analysis = apply_engine_analysis
        self._engine_analyzer = EngineAnalyzer(vehicle_configuration)
        self._apply_trip_state = apply_trip_state
        self._apply_position_state = apply_position_state
        self._apply_attitude_state = apply_attitude_state
        self._pending_ui: SimpleQueue[Callable[[], None]] = SimpleQueue()
        self._closing = False
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
            TRIP_STATE_TOPIC,
            decode_trip_state,
            self._on_trip_message,
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

    def set_vehicle_configuration(
        self,
        configuration: VehicleConfiguration,
    ) -> None:
        """Apply vehicle-specific interpretation settings to future snapshots."""
        self._engine_analyzer = EngineAnalyzer(configuration)

    def start(self) -> None:
        """Start UI draining on the Tk thread, then start transport ingress."""
        self._closing = False
        self._schedule_ui(0, self._drain_ui_queue)
        self._dispatcher.start()

    def close(self) -> None:
        self._closing = True
        self._dispatcher.close()
        self._discard_pending_ui()

    def _schedule_state(self, callback: Callable[[], None]) -> None:
        """Queue UI work without crossing into Tk from a dispatcher worker.

        MessageDispatcher handlers run on ThreadPoolExecutor workers. Calling
        ``Tk.after`` from those workers can block waiting for Tk's main loop,
        particularly while the window is being destroyed. Keep that boundary
        thread-safe by making workers enqueue callbacks only. ``start()``
        installs the queue drain from the UI thread before ingress begins.
        """
        if not self._closing:
            self._pending_ui.put(callback)

    def _drain_ui_queue(self) -> None:
        """Apply pending presentation state from the Tk/main thread."""
        if self._closing:
            self._discard_pending_ui()
            return

        while True:
            try:
                callback = self._pending_ui.get_nowait()
            except Empty:
                break
            callback()

        if not self._closing:
            self._schedule_ui(self._UI_DRAIN_INTERVAL_MS, self._drain_ui_queue)

    def _discard_pending_ui(self) -> None:
        while True:
            try:
                self._pending_ui.get_nowait()
            except Empty:
                return

    def _on_vehicle_message(self, message) -> None:
        state = VehiclePresenter.present(message.data)
        analysis = self._engine_analyzer.analyze(message.data)
        self._schedule_state(
            lambda: (
                self._apply_vehicle_state(state),
                self._apply_engine_analysis(analysis),
            )
        )

    def _on_trip_message(self, message) -> None:
        state = TripPresenter.present(message.data)
        self._schedule_state(lambda: self._apply_trip_state(state))

    def _on_position_message(self, message) -> None:
        state = NavigationPresenter.present_position(message.data)
        self._schedule_state(lambda: self._apply_position_state(state))

    def _on_attitude_message(self, message) -> None:
        state = NavigationPresenter.present_attitude(message.data)
        self._schedule_state(lambda: self._apply_attitude_state(state))

    @staticmethod
    def _on_bus_error(topic, error: Exception) -> None:
        print(f"WARNING: {topic}: {type(error).__name__}: {error}")
