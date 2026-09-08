# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Resolved runtime theme package shared by controllers and frontends."""

from __future__ import annotations

from dataclasses import dataclass

from .style_sheet import StyleSheet
from .ui_theme import UiTheme


@dataclass(frozen=True, slots=True)
class ThemeBundle:
    """A semantic UI theme plus its component-specific style rules."""

    ui: UiTheme
    style_sheet: StyleSheet
