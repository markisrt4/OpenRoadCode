# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Construct ORC application themes from packaged stylesheets."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from controllers.theme import ThemeController
from ui.theme import ThemeBundle, ThemeMode, load_theme_bundle

_THEME_ROOT = Path(__file__).resolve().parents[2] / "resources" / "themes"
_THEME_FILES = {
    ThemeMode.DARK: "orc-dark.css",
    ThemeMode.LIGHT: "orc-light.css",
}


@lru_cache(maxsize=len(_THEME_FILES))
def theme_bundle(mode: ThemeMode) -> ThemeBundle:
    """Return the packaged theme bundle for ``mode``.

    The parsed CSS bundle is immutable presentation data, so it is safe to
    share between panels instead of reparsing the same stylesheet whenever a
    panel is constructed.
    """

    try:
        filename = _THEME_FILES[mode]
    except KeyError as exc:
        raise ValueError(f"No packaged ORC theme for {mode.value}") from exc
    return load_theme_bundle(_THEME_ROOT / filename)


def create_theme_controller(
    initial_mode: ThemeMode = ThemeMode.DARK,
) -> ThemeController:
    """Create a controller backed by the packaged ORC CSS themes."""

    themes = {mode: theme_bundle(mode) for mode in _THEME_FILES}
    return ThemeController(themes, initial_mode=initial_mode)
