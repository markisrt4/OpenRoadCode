# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""OpenRoadCode automotive UI composition root."""

from __future__ import annotations

import tkinter as tk

from apps.launchers.sdrpp_launcher import sync_sdrpp_theme
from apps.orcUi.orc_ui_app import OrcUiApp
from apps.orcUi.radio_entry_panel import RadioEntryPanel
from apps.orcUi.theme_runtime import theme_bundle
from frontends.tk.games import GamesScreen
from frontends.tk.radio import RadioScreen
from frontends.x11 import X11WindowEmbedder
from ui.theme import ThemeBundle, ThemeMode

__all__ = ["OrcUiApp", "main"]


def _create_radio_panel(
    parent: tk.Misc,
    embedder: X11WindowEmbedder,
    theme: ThemeBundle,
) -> RadioEntryPanel:
    return RadioEntryPanel(parent, embedder=embedder, theme=theme)


def _sync_radio_theme(mode: ThemeMode) -> None:
    sync_sdrpp_theme("Light" if mode is ThemeMode.LIGHT else "Dark")


def main() -> None:
    """Compose and run the integrated OpenRoadCode UI."""
    app = OrcUiApp()
    app.register_screen(
        "RADIO",
        RadioScreen(
            app,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            theme_mode=lambda: app.theme_mode,
            panel_factory=_create_radio_panel,
            sync_theme=_sync_radio_theme,
        ),
    )
    app.register_screen(
        "GAMES",
        GamesScreen(app, theme_mode=lambda: app.theme_mode),
    )
    app.run()


if __name__ == "__main__":
    main()
