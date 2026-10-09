# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Narrow application service used by the orcUi radio presentation."""

from __future__ import annotations

from threading import Lock, RLock

from ui.radio.rf_radio_if import RadioApplication as RadioApplicationServiceIf

from apps.launchers.managed_sdrpp_launcher import ManagedSDRPPLauncher
from controllers.application_runtime import AppRuntimeManager


class ManagedRadioApplicationService:
    """Bridge radio presentation requests into shared application lifecycle policy."""

    APP_KEY = "sdrpp"

    def __init__(
        self,
        manager: AppRuntimeManager,
        launcher: ManagedSDRPPLauncher,
        *,
        fullscreen: bool = False,
    ) -> None:
        self._manager = manager
        self._launcher = launcher
        self._fullscreen = fullscreen
        self._closed = False
        self._state_lock = Lock()
        self._operation_lock = RLock()

    def present(self) -> None:
        """Serialize launch with terminal runtime shutdown."""
        with self._operation_lock:
            with self._state_lock:
                if self._closed:
                    raise RuntimeError("Radio application service is closed")
            self._present()

    def _present(self) -> None:
        # Embedded SDR++ must never be presented as a normal top-level window.
        # Start it directly and let RadioPanel reparent the X11 client once it
        # appears. AppRuntimeManager.show() intentionally marks/maps windowed
        # applications, which is correct for standalone mode but wrong here.
        if not self._fullscreen:
            if not self._manager.is_running(self.APP_KEY):
                self._launcher.prepare(self._manager.display_for(self.APP_KEY))
            return
        self._manager.show(self.APP_KEY)

    def window_process_id(self, *, timeout_seconds: float) -> int:
        return self._launcher.window_process_id(timeout_seconds=timeout_seconds)

    @property
    def presented(self) -> bool:
        return self._manager.is_visible(self.APP_KEY)

    @property
    def fullscreen(self) -> bool:
        return self._fullscreen

    def relinquish_for_adsb(self) -> None:
        with self._operation_lock:
            self._manager.stop(self.APP_KEY)

    def close(self) -> None:
        """Reject new launches, then stop any launch already in progress."""
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
        with self._operation_lock:
            self._manager.stop(self.APP_KEY)
