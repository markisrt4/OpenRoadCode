# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Coordinate host lifecycle actions requested by a UI."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import logging
from collections.abc import Callable
from enum import Enum

from common.logging.lifecycle import failure_fields
from common.logging.structured import current_operation, event, operation

from ui.system.lifecycle_request_handler_if import SystemLifecycleRequestHandlerIf

LOGGER = logging.getLogger("runtime.host")


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
        self._operation_id: str | None = None

    @property
    def requested_action(self) -> SystemLifecycleAction:
        """Return the most recent deferred lifecycle request."""
        return self._action

    def request_restart_ui(self) -> None:
        """Record a UI restart request without replacing the process yet."""
        self._record_action(SystemLifecycleAction.RESTART_UI)

    def request_poweroff(self) -> None:
        """Record a host poweroff request without touching the OS yet."""
        self._record_action(SystemLifecycleAction.POWEROFF)

    def _record_action(self, action: SystemLifecycleAction) -> None:
        if self._action == action:
            return
        self._action = action
        with operation(current_operation()) as operation_id:
            self._operation_id = operation_id
            event(
                LOGGER,
                logging.INFO,
                "host.action_requested",
                "Deferred host action requested",
                action=action.value,
            )

    def clear(self) -> None:
        """Discard any pending lifecycle action."""
        if self._action is not SystemLifecycleAction.NONE:
            with operation(self._operation_id):
                event(
                    LOGGER,
                    logging.INFO,
                    "host.action_cleared",
                    "Deferred host action cleared",
                    action=self._action.value,
                )
        self._action = SystemLifecycleAction.NONE
        self._operation_id = None

    def execute_requested_action(self) -> bool:
        """Execute the deferred action after application-owned resources close.

        Returns True when an action was dispatched. A restart replaces the
        current process and therefore does not normally return.
        """
        action = self._action
        self._action = SystemLifecycleAction.NONE
        if action is SystemLifecycleAction.NONE:
            return False
        operation_id = self._operation_id
        self._operation_id = None
        with operation(operation_id or current_operation()):
            event(
                LOGGER,
                logging.INFO,
                "host.dispatch_requested",
                "Host action dispatch requested",
                action=action.value,
            )
            try:
                dispatched = self._dispatch_action(action)
            except Exception as error:
                event(
                    LOGGER,
                    logging.ERROR,
                    "host.dispatch_failed",
                    "Host action dispatch failed",
                    action=action.value,
                    **failure_fields(error),
                )
                raise
            if dispatched:
                event(
                    LOGGER,
                    logging.INFO,
                    "host.action_dispatched",
                    "Host action dispatched",
                    action=action.value,
                )
            else:
                event(
                    LOGGER,
                    logging.WARNING,
                    "host.action_unavailable",
                    "Host action unavailable",
                    action=action.value,
                )
            return dispatched

    def _dispatch_action(self, action: SystemLifecycleAction) -> bool:
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
