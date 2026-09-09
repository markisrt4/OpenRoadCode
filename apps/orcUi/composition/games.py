# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose the games destination."""

from apps.orcUi.orc_ui_app import OrcUiApp
from apps.orcUi.theme_runtime import theme_bundle
from frontends.tk.games import GamesScreen


def configure_games(app: OrcUiApp) -> None:
    app.register_screen("GAMES", GamesScreen(
        app, theme_bundle=lambda: theme_bundle(app.theme_mode),
        theme_mode=lambda: app.theme_mode,
    ))
