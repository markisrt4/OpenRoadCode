# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from apps.launchers.process_manager import close_display_apps


class SystemController:
    """Perform host-level system operations used by the Car UI."""

    def __init__(self, remote_display: str) -> None:
        self._remote_display = remote_display

    def close_display_apps(self) -> None:
        close_display_apps(display=self._remote_display)