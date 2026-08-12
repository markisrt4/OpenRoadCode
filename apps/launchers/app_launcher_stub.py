# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from apps.launchers.app_launcher_if import (
    AppLauncherIf,
    StatusCallback,
)


class AppLauncherStub(AppLauncherIf):
    """Silent deterministic launcher stub for consumers and tests."""

    def __init__(self, running: bool = False) -> None:
        self._running = running

    def launch(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        self._running = True

    def stop(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        self._running = False

    def toggle(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> bool:
        self._running = not self._running
        return self._running

    def is_running(self) -> bool:
        return self._running
