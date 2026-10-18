# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Focus and completion operations supplied by a native or browser adapter."""
from typing import Protocol


class TextInputTargetIf(Protocol):
    """Operate a field without exposing its widget, browser, or text contents."""

    def focus(self) -> None:
        """Focus this field without changing its contents."""
        ...

    def submit(self) -> None:
        """Apply the field's normal submit action."""
        ...

    def cancel(self) -> None:
        """Apply the field's cancel action; rollback policy belongs to the target."""
        ...
