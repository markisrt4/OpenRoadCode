# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own asynchronous permission-page launch and obsolete completion handling."""

import threading
from dataclasses import replace
from collections.abc import Callable
from typing import Protocol

from ui.navigation.host_location_ui_if import HostLocationState, HostLocationUiIf
from ui.ui_dispatcher_if import UiDispatcherIf


class HostLocationPermissionIf(Protocol):
    def open_permission_page(self, cancelled: Callable[[], bool]) -> None:
        """Check service availability and open the host location permission window."""
        ...

    def restore_if_running(self, cancelled: Callable[[], bool]) -> None:
        """Reconnect an existing permission page without opening a new window."""
        ...


class HostLocationSettingsController:
    def __init__(self, dispatcher: UiDispatcherIf, ui: HostLocationUiIf,
                 permission: HostLocationPermissionIf, *, available: bool = True) -> None:
        self._dispatcher, self._ui, self._permission = dispatcher, ui, permission
        self._generation = 0
        self._visible = False
        self._closed = False
        self._state = (HostLocationState() if available else HostLocationState(
            "Termux location uses the Android sensor bridge.", can_share=False))

    def show(self) -> None:
        if not self._closed:
            self._visible = True
            self._ui.set_host_location_state(self._state)

    def restore_if_running(self):
        def work():
            try:
                self._permission.restore_if_running(lambda: self._closed)
            except (OSError, RuntimeError):
                pass  # The normal Share action remains available for recovery.
        if self._state.can_share:
            threading.Thread(target=work, name='host-location-restore', daemon=True).start()

    def hide(self) -> None:
        self._visible = False
        self._generation += 1
        if self._state.busy:
            self._state = replace(self._state, status=HostLocationState().status, busy=False)

    def close(self) -> None:
        self.hide()
        self._closed = True

    def share_host_location(self) -> None:
        if not self._visible or self._closed or self._state.busy or self._state.sharing or not self._state.can_share:
            return
        self._generation += 1
        generation = self._generation
        self._state = replace(self._state, status="Preparing location sharing…", busy=True)
        self._ui.set_host_location_state(self._state)

        def cancelled() -> bool:
            return self._closed or not self._visible or generation != self._generation

        def work() -> None:
            try:
                self._permission.open_permission_page(cancelled)
                message = "In the location window, click Share host location and allow access. Keep that window open."
            except Exception as error:
                message = str(error)
            if not cancelled():
                self._dispatcher.dispatch_ui(lambda: self._complete(generation, message))

        threading.Thread(target=work, name="host-location-permission", daemon=True).start()

    def _complete(self, generation: int, message: str) -> None:
        if self._closed or not self._visible or generation != self._generation:
            return
        self._state = replace(self._state, status='Host location sharing is active.' if self._state.sharing else message, busy=False)
        self._ui.set_host_location_state(self._state)

    def update_location_status(self, location_status, android_status):
        def apply():
            if self._closed:
                return
            self._state = replace(self._state, location_status=location_status, android_status=android_status)
            if self._visible:
                self._ui.set_host_location_state(self._state)
        self._dispatcher.dispatch_ui(apply)

    def update_host_sharing(self, sharing: bool):
        def apply():
            if self._closed:
                return
            self._state = replace(self._state, sharing=sharing,
                status='Host location sharing is active.' if sharing else HostLocationState().status)
            if self._visible:
                self._ui.set_host_location_state(self._state)
        self._dispatcher.dispatch_ui(apply)
