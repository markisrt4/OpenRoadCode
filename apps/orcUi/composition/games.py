# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose the games destination."""

from apps.orcUi.theme_runtime import theme_bundle
from frontends.tk.games import GamesScreen
from frontends.tk.orc_ui.orc_ui_app import OrcUiApp


def configure_games(app: OrcUiApp) -> GamesScreen:
    """Create, register, and return the Games screen owned by composition."""
    screen = GamesScreen(
        app,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
        theme_mode=lambda: app.theme_mode,
    )
    app.register_screen("GAMES", screen)
    return screen
