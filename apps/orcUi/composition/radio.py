# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose radio presentation and feature-scoped dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from apps.launchers.sdrpp_launcher import sync_sdrpp_theme
from apps.orcUi.orc_ui_app import OrcUiApp
from apps.orcUi.radio_entry_panel import RadioEntryPanel
from apps.orcUi.theme_runtime import theme_bundle
from controllers.radio.adapters.radio_browser_directory import RadioBrowserDirectory
from controllers.radio.streaming_radio_favorites import StreamingRadioFavorites
from frontends.tk.radio import RadioScreen
from ui.theme import ThemeMode


@dataclass(slots=True)
class RadioComposition:
    """Own radio presentation resources created by the composition root."""

    screen: RadioScreen
    directory: RadioBrowserDirectory
    favorites: StreamingRadioFavorites


def configure_radio(app: OrcUiApp, runtime) -> RadioComposition:
    """Compose radio UI against runtime-owned playback and SDR services."""

    def sync_theme(mode: ThemeMode) -> None:
        sync_sdrpp_theme("Light" if mode is ThemeMode.LIGHT else "Dark")

    directory = RadioBrowserDirectory(timeout_s=10.0)
    favorites = StreamingRadioFavorites()
    screen = RadioScreen(
        app,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
        theme_mode=lambda: app.theme_mode,
        panel_factory=lambda parent, embedder, theme: RadioEntryPanel(
            parent,
            embedder=embedder,
            theme=theme,
            radio_application=runtime.radio,
            streaming_radio=runtime.streaming_radio,
            directory=directory,
            favorites=favorites,
        ),
        sync_theme=sync_theme,
    )
    app.register_screen("RADIO", screen)
    return RadioComposition(screen=screen, directory=directory, favorites=favorites)
