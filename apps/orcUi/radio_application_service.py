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


class ManagedRadioApplicationService:
    """Bridge radio presentation requests into shared application lifecycle policy."""

    APP_KEY = "sdrpp"

    def __init__(
        self,
        manager: AppRuntimeManager,
        launcher: ManagedSDRPPLauncher,
    ) -> None:
        self._manager = manager
        self._launcher = launcher

    def present(self) -> None:
        self._manager.show(self.APP_KEY)

    def window_process_id(self, *, timeout_seconds: float) -> int:
        return self._launcher.window_process_id(timeout_seconds=timeout_seconds)
