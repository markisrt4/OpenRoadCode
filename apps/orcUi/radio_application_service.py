# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Narrow application service used by the orcUi radio presentation."""

from __future__ import annotations

from typing import Protocol

from apps.launchers.managed_sdrpp_launcher import ManagedSDRPPLauncher
from controllers.application_runtime import AppRuntimeManager


class RadioApplicationServiceIf(Protocol):
    """Presentation-facing operations for the managed RF radio application."""

    def present(self) -> None:
        """Ensure the managed radio application is running and presentable."""

    def window_process_id(self, *, timeout_seconds: float) -> int:
        """Return the X11 client process id used for embedding."""

    @property
    def presented(self) -> bool:
        """Return whether RF radio is currently presented to the user."""

    @property
    def fullscreen(self) -> bool:
        """Return whether RF is configured for native fullscreen presentation."""

    def relinquish_for_adsb(self) -> None:
        """Stop RF presentation so an explicit ADS-B request can use the SDR."""


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

    def present(self) -> None:
        # A preloaded SDR++ window must remain hidden until the X11 embedder
        # reparents it. Mapping it here creates a competing top-level window.
        if self._manager.is_running(self.APP_KEY) and not self._fullscreen:
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
        self._manager.stop(self.APP_KEY)
