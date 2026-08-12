# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable no-op implementation of the common UI lifecycle."""

from ui.ui_if import UiIf


class UiStub(UiIf):
    """Provide a successful, idempotent no-op UI lifecycle."""

    def initialize(self) -> bool:
        return True

    def run(self) -> None:
        pass

    def shutdown(self) -> None:
        pass
