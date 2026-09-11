# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Inert lifecycle request handler for tests and unavailable integrations."""

from ui.system.lifecycle_request_handler_if import SystemLifecycleRequestHandlerIf


class SystemLifecycleRequestHandlerStub(SystemLifecycleRequestHandlerIf):
    """Record the latest lifecycle request without touching the host system."""

    def __init__(self) -> None:
        self.restart_ui_requested = False
        self.poweroff_requested = False

    def request_restart_ui(self) -> None:
        self.restart_ui_requested = True

    def request_poweroff(self) -> None:
        self.poweroff_requested = True
