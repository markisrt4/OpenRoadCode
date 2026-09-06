# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""OpenRoadCode automotive UI composition root."""

from __future__ import annotations

import tkinter as tk

from apps.launchers.sdrpp_launcher import sync_sdrpp_theme
from apps.orcUi.application_runtime import create_orc_ui_application_runtime
from apps.orcUi.orc_ui_app import OrcUiApp
from apps.orcUi.radio_application_service import RadioApplicationServiceIf
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
    radio_application: RadioApplicationServiceIf,
) -> RadioEntryPanel:
    return RadioEntryPanel(
        parent,
        embedder=embedder,
        theme=theme,
        radio_application=radio_application,
    )


def _sync_radio_theme(mode: ThemeMode) -> None:
    sync_sdrpp_theme("Light" if mode is ThemeMode.LIGHT else "Dark")


def main() -> None:
    """Compose and run the integrated OpenRoadCode UI."""
    application_runtime = create_orc_ui_application_runtime()
    app = OrcUiApp()
    app.register_screen(
        "RADIO",
        RadioScreen(
            app,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            theme_mode=lambda: app.theme_mode,
            panel_factory=lambda parent, embedder, theme: _create_radio_panel(
                parent,
                embedder,
                theme,
                application_runtime.radio,
            ),
            sync_theme=_sync_radio_theme,
        ),
    )
    app.register_screen(
        "GAMES",
        GamesScreen(app, theme_mode=lambda: app.theme_mode),
    )

    # Keep heavyweight optional applications out of the critical UI startup
    # path. Once Tk has presented the shell, the shared lifecycle controller
    # applies PRELOAD/PERSISTENT policy on its background worker.
    app.schedule_ui_callback(1500, application_runtime.start_background_apps)
    try:
        app.run()
    finally:
        application_runtime.close()


if __name__ == "__main__":
    main()
