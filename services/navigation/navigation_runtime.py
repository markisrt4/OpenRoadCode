# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own one navigation controller and expose telemetry plus commands."""

from __future__ import annotations

import threading
import time

from controllers.navigation.navigation_controller_if import NavigationControllerIf
from controllers.route_planning.route_planning_controller_if import RoutePlanningControllerIf
from messaging.contracts.navigation import NavigationStatePublisher
from services.navigation.navigation_command_service import NavigationCommandService
from services.navigation.zeromq_navigation_command_server import (
    DEFAULT_NAVIGATION_COMMAND_ENDPOINT,
    ZeroMqNavigationCommandServer,
)


class NavigationRuntime:
    """Run navigation telemetry and commands against one controller instance."""

    def __init__(
        self,
        controller: NavigationControllerIf,
        publisher,
        *,
        source: str,
        rate_hz: float = 10.0,
        command_endpoint: str = DEFAULT_NAVIGATION_COMMAND_ENDPOINT,
        route_planning_controller: RoutePlanningControllerIf | None = None,
    ) -> None:
        if rate_hz <= 0.0:
            raise ValueError("rate_hz must be greater than zero")
        self._controller = controller
        self._state_publisher = NavigationStatePublisher(publisher, source=source)
        self._period_s = 1.0 / rate_hz
        self._command_server = ZeroMqNavigationCommandServer(
            NavigationCommandService(
                controller,
                route_planning_controller=route_planning_controller,
            ),
            command_endpoint,
        )
        self._command_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the controller and command server."""
        self._controller.start()
        self._stop_event.clear()
        self._command_thread = threading.Thread(
            target=self._command_server.run,
            name="navigation-command-server",
            daemon=True,
        )
        self._command_thread.start()

    def run(self) -> None:
        """Publish controller snapshots until close() is called."""
        self.start()
        try:
            while not self._stop_event.is_set():
                started = time.monotonic()
                self._state_publisher.publish(self._controller.read_state())
                remaining = self._period_s - (time.monotonic() - started)
                if remaining > 0.0:
                    self._stop_event.wait(remaining)
        finally:
            self.close()

    def close(self) -> None:
        """Stop command handling and release the owned controller."""
        self._stop_event.set()
        self._command_server.close()
        thread = self._command_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._command_thread = None
        self._controller.stop()
