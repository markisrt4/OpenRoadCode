# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op application status UI implementation."""

from ui.system.status_ui_if import StatusUiIf, StatusValue


class StatusUiStub(StatusUiIf):
    """Ignore application status updates."""

    def set_status(self, status: StatusValue) -> None:
        pass
