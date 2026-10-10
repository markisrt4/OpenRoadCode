# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation operations used by the installer destination flow."""

from abc import ABC, abstractmethod


class DestinationSetupUiIf(ABC):
    @abstractmethod
    def choose(self, title: str, prompt: str, choices: tuple[tuple[str, str], ...]) -> str | None:
        """Present choices.

        @param title Dialog title.
        @param prompt Instructions.
        @param choices Stable keys and display labels.
        @return Selected key, or None on cancellation.
        """
        ...

    @abstractmethod
    def text(self, title: str, prompt: str, initial: str = "") -> str | None:
        """Read user text.

        @param title Dialog title.
        @param prompt Instructions.
        @param initial Existing value.
        @return Entered text, or None on cancellation.
        """
        ...

    @abstractmethod
    def confirm(self, title: str, prompt: str) -> bool:
        """Ask for confirmation.

        @param title Dialog title.
        @param prompt Proposed destination.
        @return True only when confirmed.
        """
        ...

    @abstractmethod
    def notify(self, title: str, message: str) -> None:
        """Show feedback.

        @param title Dialog title.
        @param message User-facing feedback.
        """
        ...
