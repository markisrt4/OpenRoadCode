# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose radio presentation and feature-scoped dependencies."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

from apps.launchers.sdrpp_launcher import sync_sdrpp_theme
from apps.orcUi.adapters.adsb_control import OrcUiAdsbControl
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.frontend.tk.radio_entry_panel import RadioEntryPanel
from apps.orcUi.theme_runtime import theme_bundle
from controllers.radio.adapters.radio_browser_directory import RadioBrowserDirectory
from controllers.radio.radio_profile_controller import RadioProfileController
from controllers.radio.streaming_radio_favorites import StreamingRadioFavorites
from frontends.tk.radio import RadioScreen
from frontends.tk.radio.streaming_radio_now_playing import StreamingRadioNowPlaying
from ui.theme import ThemeMode


@dataclass(slots=True)
class RadioComposition:
    """Own radio presentation resources created by the composition root."""

    screen: RadioScreen
    directory: RadioBrowserDirectory
    favorites: StreamingRadioFavorites
    home_factory: Callable[[tk.Misc], tk.Widget]
    open_weather_radio: Callable[[], None]


def configure_radio(app: OrcUiApp, runtime) -> RadioComposition:
    """Compose radio UI against runtime-owned playback and SDR services."""

    def sync_theme(mode: ThemeMode) -> None:
        sync_sdrpp_theme("Light" if mode is ThemeMode.LIGHT else "Dark")

    directory = RadioBrowserDirectory(timeout_s=10.0)
    favorites = StreamingRadioFavorites()
    adsb = OrcUiAdsbControl()
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
            adsb_control=adsb,
            on_location_changed=lambda leaf: app.set_breadcrumb("RADIO", leaf),
        ),
        sync_theme=sync_theme,
        on_location_changed=lambda leaf: app.set_breadcrumb("RADIO", leaf),
    )
    app.register_screen("RADIO", screen)

    def show_radio_source(source: str) -> None:
        """Navigate through the shell before opening a radio source."""
        app.navigate_to("RADIO")
        if source == "rf":
            screen.open_rf()
        elif source == "streaming":
            screen.open_streaming()
        elif source == "adsb":
            screen.open_adsb()
        else:
            raise ValueError(f"Unsupported radio source: {source}")

    def open_weather_radio() -> None:
        """Start NOAA RF audio while leaving the requesting screen visible."""
        app.set_screen_status("RF: starting NOAA Weather Radio")
        controller = RadioProfileController()
        profile = controller.catalog.profile("weather_band")
        if not profile.presets:
            app.set_screen_status("RF: no NOAA weather presets configured")
            return
        preset = profile.presets[0]
        try:
            runtime.radio.present()
        except (OSError, RuntimeError, ValueError) as error:
            app.set_screen_status(f"RF: {error}")
            return

        def tune_when_ready(attempts_remaining: int = 24) -> None:
            try:
                if controller.active_profile_key != profile.key:
                    controller.select_profile(profile.key)
                state = controller.tune_preset(preset)
            except (OSError, RuntimeError, ValueError) as error:
                if attempts_remaining > 0:
                    app.schedule_ui_callback(
                        250,
                        lambda: tune_when_ready(attempts_remaining - 1),
                    )
                    return
                app.set_screen_status(f"RF: {error}")
                return
            app.set_screen_status(
                f"RF: Playing {preset.frequency_hz / 1_000_000:.3f} MHz · {state.label}"
            )

        app.schedule_ui_callback(250, tune_when_ready)

    def home_radio_factory(parent):
        return StreamingRadioNowPlaying(
            parent,
            controller=runtime.streaming_radio,
            theme=theme_bundle(app.theme_mode),
            on_open_rf=lambda: show_radio_source("rf"),
            on_open_streaming=lambda: show_radio_source("streaming"),
            on_open_adsb=lambda: show_radio_source("adsb"),
        )

    def toggle_adsb(enabled: bool) -> bool:
        # An explicit ADS-B selection wins the shared SDR. Relinquish RF first.
        if enabled and runtime.radio.presented:
            runtime.radio.relinquish_for_adsb()
        try:
            return adsb.set_tracking(enabled)
        except (OSError, RuntimeError, ValueError) as error:
            app.set_screen_status(f"ADS-B: {error}")
            return adsb.tracking

    app.set_adsb_handlers(
        on_toggle=toggle_adsb,
        on_view=lambda: show_radio_source("adsb"),
    )
    app.set_adsb_state(enabled=adsb.tracking, aircraft_count=adsb.aircraft_count)

    def refresh_adsb_status() -> None:
        app.set_adsb_state(enabled=adsb.tracking, aircraft_count=adsb.aircraft_count)
        app.schedule_ui_callback(1000, refresh_adsb_status)

    app.schedule_ui_callback(1000, refresh_adsb_status)
    return RadioComposition(
        screen=screen,
        directory=directory,
        favorites=favorites,
        home_factory=home_radio_factory,
        open_weather_radio=open_weather_radio,
    )
