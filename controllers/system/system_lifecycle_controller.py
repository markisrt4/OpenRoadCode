# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Coordinate host lifecycle actions requested by a UI."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from enum import Enum

from ui.system.lifecycle_request_handler_if import SystemLifecycleRequestHandlerIf


class SystemLifecycleAction(str, Enum):
    """Deferred host action requested by the UI."""

    NONE = "none"
    RESTART_UI = "restart-ui"
    POWEROFF = "poweroff"


class SystemLifecycleController(SystemLifecycleRequestHandlerIf):
    """Record lifecycle intent and execute it only after application cleanup."""

    def __init__(
        self,
        *,
        executable: str | None = None,
        execv: Callable[[str, list[str]], object] = os.execv,
        which: Callable[[str], str | None] = shutil.which,
        popen: Callable[[list[str]], object] = subprocess.Popen,
    ) -> None:
        self._action = SystemLifecycleAction.NONE
        self._executable = executable or sys.executable
        self._execv = execv
        self._which = which
        self._popen = popen

    @property
    def requested_action(self) -> SystemLifecycleAction:
        """Return the most recent deferred lifecycle request."""
        return self._action

    def request_restart_ui(self) -> None:
        """Record a UI restart request without replacing the process yet."""
        self._action = SystemLifecycleAction.RESTART_UI

    def request_poweroff(self) -> None:
        """Record a host poweroff request without touching the OS yet."""
        self._action = SystemLifecycleAction.POWEROFF

    def clear(self) -> None:
        """Discard any pending lifecycle action."""
        self._action = SystemLifecycleAction.NONE

    def execute_requested_action(self) -> bool:
        """Execute the deferred action after application-owned resources close.

        Returns True when an action was dispatched. A restart replaces the
        current process and therefore does not normally return.
        """
        action = self._action
        self._action = SystemLifecycleAction.NONE
        if action is SystemLifecycleAction.NONE:
            return False
        if action is SystemLifecycleAction.RESTART_UI:
            self._execv(
                self._executable,
                [self._executable, "-m", "apps.orcUi"],
            )
            return True

        command = self._poweroff_command()
        if command is None:
            return False
        self._popen(command)
        return True

    def _poweroff_command(self) -> list[str] | None:
        if self._which("systemctl"):
            return ["systemctl", "poweroff"]
        if self._which("loginctl"):
            return ["loginctl", "poweroff"]
        return None
