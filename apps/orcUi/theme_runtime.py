# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Construct the ORC application theme controller from packaged stylesheets."""

from __future__ import annotations

from pathlib import Path

from controllers.theme import ThemeController
from ui.theme import ThemeMode, load_theme_bundle

_THEME_ROOT = Path(__file__).resolve().parents[2] / "resources" / "themes"
_THEME_FILES = {
    ThemeMode.DARK: "orc-dark.css",
    ThemeMode.LIGHT: "orc-light.css",
}


def create_theme_controller(
    initial_mode: ThemeMode = ThemeMode.DARK,
) -> ThemeController:
    """Create a controller backed by the packaged ORC CSS themes."""

    themes = {
        mode: load_theme_bundle(_THEME_ROOT / filename)
        for mode, filename in _THEME_FILES.items()
    }
    return ThemeController(themes, initial_mode=initial_mode)
