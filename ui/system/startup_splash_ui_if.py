# SPDX-License-Identifier: MIT
"""Presentation requests for the startup splash."""

from typing import Protocol


class StartupSplashUiIf(Protocol):
    def show_failure(self, detail: str) -> None:
        """Display startup failure.

        @param detail Local diagnostic text.
        """
        ...

    def close(self) -> None:
        """Dismiss the splash after the dashboard is ready."""
        ...
