# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract for independently composed orcUi navigation features."""

from __future__ import annotations

from abc import ABC, abstractmethod

import tkinter as tk

from apps.orcUi.orc_theme import ThemeMode


class OrcUiFeatureIf(ABC):
    """Feature mounted into the orcUi shell through composition."""

    @property
    @abstractmethod
    def nav_name(self) -> str:
        """Return the side-navigation label used to activate the feature."""

    @property
    @abstractmethod
    def nav_order(self) -> int:
        """Return the feature's position in the side-navigation ordering."""

    @abstractmethod
    def show(
        self,
        *,
        root: tk.Tk,
        content: tk.Frame,
        theme_mode: ThemeMode,
    ) -> None:
        """Mount the feature into the provided content frame."""

    @abstractmethod
    def hide(self) -> None:
        """Release active UI/runtime state before the shell destroys content."""

    @abstractmethod
    def theme_changed(self, theme_mode: ThemeMode) -> None:
        """Apply a shell theme change to any active feature UI/runtime."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release feature resources during application shutdown."""
