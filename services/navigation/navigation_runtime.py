# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own one navigation controller and expose telemetry plus commands."""

from __future__ import annotations

import threading
import time

from controllers.navigation.navigation_controller_if import NavigationControllerIf
from messaging.contracts.navigation.navigation_state_publisher import NavigationStatePublisher
from services.navigation.navigation_command_service import NavigationCommandService
from services.navigation.zeromq_navigation_command_server import DEFAULT_NAVIGATION_COMMAND_ENDPOINT, ZeroMqNavigationCommandServer


class NavigationRuntime:
    """Run navigation telemetry and commands against one controller instance."""

    def __init__(self, controller: NavigationControllerIf, publisher, *, source: str, rate_hz: float = 10.0, command_endpoint: str = DEFAULT_NAVIGATION_COMMAND_ENDPOINT) -> None:
        if rate_hz <= 0.0:
            raise ValueError("rate_hz must be greater than zero")
        self._controller = controller
        self._state_publisher = NavigationStatePublisher(publisher, source=source)
        self._period_s = 1.0 / rate_hz
        self._command_server = ZeroMqNavigationCommandServer(NavigationCommandService(controller), command_endpoint)
        self._command_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._controller_started = False

    def start(self) -> None:
        """Bind command transport first, then start owned runtime resources."""
        self._stop_event.clear()
        self._command_server.bind()
        try:
            self._controller.start()
            self._controller_started = True
            self._command_thread = threading.Thread(target=self._command_server.run, name="navigation-command-server", daemon=True)
            self._command_thread.start()
        except Exception:
            self._command_server.close()
            raise

    def run(self) -> None:
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
        self._stop_event.set()
        self._command_server.close()
        thread = self._command_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._command_thread = None
        if self._controller_started:
            self._controller.stop()
            self._controller_started = False
