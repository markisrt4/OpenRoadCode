# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose radio presentation without owning external application lifecycle."""

from apps.launchers.sdrpp_launcher import sync_sdrpp_theme
from apps.orcUi.orc_ui_app import OrcUiApp
from apps.orcUi.radio_entry_panel import RadioEntryPanel
from apps.orcUi.theme_runtime import theme_bundle
from frontends.tk.radio import RadioScreen
from ui.theme import ThemeMode


def configure_radio(app: OrcUiApp, runtime) -> None:
    def sync_theme(mode: ThemeMode) -> None:
        sync_sdrpp_theme("Light" if mode is ThemeMode.LIGHT else "Dark")

    app.register_screen("RADIO", RadioScreen(
        app,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
        theme_mode=lambda: app.theme_mode,
        panel_factory=lambda parent, embedder, theme: RadioEntryPanel(
            parent, embedder=embedder, theme=theme, radio_application=runtime.radio,
        ),
        sync_theme=sync_theme,
    ))
