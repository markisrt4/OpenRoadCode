# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors

"""Compose the Spotify palette from the active ORC theme."""

from __future__ import annotations

import copy

from apps.common.uiTheme.spotify import SPOTIFY_PANEL_THEME
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.theme_runtime import theme_bundle

SPOTIFY_GREEN = "#1DB954"


def spotify_theme(app: OrcUiApp) -> dict:
    """Use active CSS for chrome and Spotify green for provider actions."""
    theme = copy.deepcopy(SPOTIFY_PANEL_THEME)
    ui = theme_bundle(app.theme_mode).ui
    theme["colors"].update(
        {
            "background": ui.background,
            "card_background": ui.surface,
            "card_border": ui.border,
            "title": ui.text,
            "subtitle": ui.text_muted,
            "detail": ui.text_muted,
            "status": ui.accent_success,
            "button_background": ui.control_background,
            "button_foreground": ui.control_text,
            "button_active_background": SPOTIFY_GREEN,
            "button_active_foreground": "#000000",
            "button_disabled_foreground": ui.text_muted,
            "progress_track": ui.border,
            "progress_fill": SPOTIFY_GREEN,
        }
    )
    return theme
