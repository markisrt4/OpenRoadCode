# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Platform boundary for an existing system on-screen keyboard."""
from typing import Protocol


class SoftKeyboardIf(Protocol):
    @property
    def available(self) -> bool:
        """Whether this backend is configured and available."""
        ...

    def show(self) -> None:
        """Request keyboard display without taking text focus from the field."""
        ...

    def hide(self) -> None:
        """Hide only the keyboard surface owned by this adapter."""
        ...

    def close(self) -> None:
        """Release owned keyboard resources; safe to repeat."""
        ...
