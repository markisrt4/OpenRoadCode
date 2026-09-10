# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose radio presentation and feature-scoped dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from apps.launchers.sdrpp_launcher import sync_sdrpp_theme
from apps.orcUi.radio_application_service import RadioApplicationServiceIf
from apps.orcUi.theme_runtime import theme_bundle
from controllers.radio.adapters.radio_browser_directory import RadioBrowserDirectory
from controllers.radio.streaming_radio_favorites import StreamingRadioFavorites
from frontends.tk.orc_ui.orc_ui_app import OrcUiApp
from frontends.tk.radio import RadioScreen
from frontends.tk.radio.radio_entry_panel import RadioEntryPanel
from frontends.tk.radio.streaming_radio_now_playing import StreamingRadioNowPlaying
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

    def show_radio_source(source: str) -> None:
        """Navigate through the shell before opening a radio source."""
        app.navigate_to("RADIO")
        if source == "rf":
            screen.open_rf()
        elif source == "streaming":
            screen.open_streaming()
        else:
            raise ValueError(f"Unsupported radio source: {source}")

    def home_radio_factory(parent):
        return StreamingRadioNowPlaying(
            parent,
            controller=runtime.streaming_radio,
            theme=theme_bundle(app.theme_mode),
            on_open_rf=lambda: show_radio_source("rf"),
            on_open_streaming=lambda: show_radio_source("streaming"),
        )

    app.set_home_radio_factory(home_radio_factory)
    return RadioComposition(screen=screen, directory=directory, favorites=favorites)
