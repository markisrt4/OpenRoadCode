# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own asynchronous permission-page launch and obsolete completion handling."""

import threading
from collections.abc import Callable
from typing import Protocol

from ui.navigation.host_location_ui_if import HostLocationState, HostLocationUiIf
from ui.ui_dispatcher_if import UiDispatcherIf


class HostLocationPermissionIf(Protocol):
    def open_permission_page(self, cancelled: Callable[[], bool]) -> None:
        """Check service availability and open the host's ordinary browser."""
        ...


class HostLocationSettingsController:
    def __init__(self, dispatcher: UiDispatcherIf, ui: HostLocationUiIf,
                 permission: HostLocationPermissionIf) -> None:
        self._dispatcher, self._ui, self._permission = dispatcher, ui, permission
        self._generation = 0
        self._visible = False
        self._closed = False
        self._state = HostLocationState()

    def show(self) -> None:
        if not self._closed:
            self._visible = True
            self._ui.set_host_location_state(self._state)

    def hide(self) -> None:
        self._visible = False
        self._generation += 1
        if self._state.busy:
            self._state = HostLocationState()

    def close(self) -> None:
        self.hide()
        self._closed = True

    def share_host_location(self) -> None:
        if not self._visible or self._closed or self._state.busy:
            return
        self._generation += 1
        generation = self._generation
        self._state = HostLocationState("Checking location service…", busy=True)
        self._ui.set_host_location_state(self._state)

        def cancelled() -> bool:
            return self._closed or not self._visible or generation != self._generation

        def work() -> None:
            try:
                self._permission.open_permission_page(cancelled)
                message = "Permission page opened. Click Share host location and allow access."
            except Exception as error:
                message = str(error)
            if not cancelled():
                self._dispatcher.schedule_ui_callback(0, lambda: self._complete(generation, message))

        threading.Thread(target=work, name="host-location-permission", daemon=True).start()

    def _complete(self, generation: int, message: str) -> None:
        if self._closed or not self._visible or generation != self._generation:
            return
        self._state = HostLocationState(message)
        self._ui.set_host_location_state(self._state)
