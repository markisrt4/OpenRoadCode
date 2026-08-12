# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Explicit UI contracts and stubs for shared system state."""

from ui.system.diagnostics_ui_if import SystemDiagnostics, SystemDiagnosticsUiIf
from ui.system.diagnostics_ui_stub import SystemDiagnosticsUiStub
from ui.system.status_ui_if import (
    StatusMessage,
    StatusSeverity,
    StatusUiIf,
    StatusValue,
)
from ui.system.status_ui_stub import StatusUiStub
from ui.system.top_bar_ui_if import TopBarUiIf
from ui.system.top_bar_ui_stub import TopBarUiStub
from ui.system.volume_request_handler_if import VolumeRequestHandlerIf
from ui.system.volume_request_handler_stub import VolumeRequestHandlerStub
from ui.system.volume_ui_if import VolumeUiIf
from ui.system.volume_ui_stub import VolumeUiStub

__all__ = [
    "StatusMessage",
    "StatusSeverity",
    "StatusUiIf",
    "StatusUiStub",
    "StatusValue",
    "SystemDiagnostics",
    "SystemDiagnosticsUiIf",
    "SystemDiagnosticsUiStub",
    "TopBarUiIf",
    "TopBarUiStub",
    "VolumeRequestHandlerIf",
    "VolumeRequestHandlerStub",
    "VolumeUiIf",
    "VolumeUiStub",
]
