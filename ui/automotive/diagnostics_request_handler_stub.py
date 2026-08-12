# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op vehicle diagnostics request handler."""

from ui.automotive.diagnostics_request_handler_if import (
    DiagnosticsRequestHandlerIf,
)


class DiagnosticsRequestHandlerStub(DiagnosticsRequestHandlerIf):
    """Ignore requests to clear vehicle diagnostics."""

    def request_clear_diagnostics(self) -> None:
        pass
