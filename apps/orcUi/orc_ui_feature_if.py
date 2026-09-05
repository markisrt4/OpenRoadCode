# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract for independently composed orcUi navigation features."""

from __future__ import annotations

from abc import ABC, abstractmethod

import tkinter as tk

from apps.orcUi.orc_theme import ThemeMode


class OrcUiFeatureIf(ABC):
    """Feature mounted into the orcUi shell through composition.

    Runtime dependencies and UI scheduling belong in the feature constructor.
    The shell supplies only the content host when a feature is activated.
    """

    @property
    @abstractmethod
    def nav_name(self) -> str:
        """Return the side-navigation label used to activate the feature."""

    @property
    @abstractmethod
    def nav_order(self) -> int:
        """Return the feature's position in side-navigation ordering."""

    @abstractmethod
    def show(self, content: tk.Frame) -> None:
        """Mount the feature into the shell-owned content frame."""

    @abstractmethod
    def hide(self) -> None:
        """Release active UI/runtime state before content is destroyed."""

    @abstractmethod
    def theme_changed(self, theme_mode: ThemeMode) -> None:
        """Apply an application theme change to active feature state."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release feature resources during application shutdown."""
