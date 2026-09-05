# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract for UI objects that accept semantic themes."""

from typing import Protocol

from .ui_theme import UiTheme


class ThemeUiIf(Protocol):
    """A UI object that can apply a complete theme at runtime."""

    def set_theme(self, theme: UiTheme) -> None:
        """Apply a theme and redraw theme-dependent presentation.

        @param theme Complete semantic UI theme to apply.
        """
        ...
