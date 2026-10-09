# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose radio presentation and feature-scoped dependencies."""

from __future__ import annotations

import tkinter as tk
import threading
from queue import Empty, SimpleQueue
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
from ui.radio import AircraftMenuRequestHandlerIf


@dataclass(frozen=True, slots=True)
class AircraftMenuRequests(AircraftMenuRequestHandlerIf):
    """Composition-owned routing for persistent Aircraft menu requests."""

    toggle_adsb: Callable[[bool], None]
    open_tracker: Callable[[], None]
    open_airband: Callable[[], None]

    def request_adsb_enabled(self, enabled: bool) -> None:
        self.toggle_adsb(enabled)

    def request_open_tracker(self) -> None:
        self.open_tracker()

    def request_open_airband(self) -> None:
        self.open_airband()


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

    network_allowed = lambda: app.online_mode.online
    runtime.streaming_radio.set_network_allowed(network_allowed)
    def mode_changed(online: bool) -> None:
        if not online:
            try:
                runtime.streaming_radio.stop()
            except (OSError, RuntimeError) as exc:
                app.set_screen_status(f"Could not stop internet radio: {exc}")
    app.online_mode.subscribe(mode_changed)
    mode_changed(app.online_mode.online)
    directory = RadioBrowserDirectory(timeout_s=10.0, network_allowed=network_allowed)
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
            online_mode=app.online_mode,
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
            if not network_allowed():
                app.set_screen_status("Offline mode: internet radio unavailable")
                return
            screen.open_streaming()
        elif source == "adsb":
            screen.open_adsb()
        elif source == "airband":
            screen.open_airband()
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
            online_allowed=network_allowed,
            theme=theme_bundle(app.theme_mode),
            on_open_rf=lambda: show_radio_source("rf"),
            on_open_streaming=lambda: show_radio_source("streaming"),
            on_open_adsb=lambda: show_radio_source("adsb"),
        )

    def toggle_adsb(enabled: bool) -> tuple[bool, str | None]:
        # An explicit ADS-B selection wins the shared SDR. Relinquish RF first.
        try:
            if enabled and runtime.radio.presented:
                runtime.radio.relinquish_for_adsb()
            return adsb.set_tracking(enabled), None
        except (OSError, RuntimeError, ValueError) as error:
            return adsb.tracking, f"ADS-B: {error}"

    adsb_io_lock = threading.Lock()
    adsb_results: SimpleQueue[tuple[bool, int, str | None]] = SimpleQueue()

    def request_adsb(enabled: bool) -> None:
        """Serialize service transitions away from the Tk event thread."""
        if not adsb_io_lock.acquire(blocking=False):
            return

        def apply() -> None:
            try:
                effective, error = toggle_adsb(enabled)
                adsb_results.put((effective, adsb.aircraft_count, error))
            finally:
                adsb_io_lock.release()

        threading.Thread(target=apply, name="orcui-adsb-state", daemon=True).start()

    app.set_aircraft_request_handler(AircraftMenuRequests(
        toggle_adsb=request_adsb,
        open_tracker=lambda: show_radio_source("adsb"),
        open_airband=lambda: show_radio_source("airband"),
    ))
    app.set_adsb_state(enabled=False, aircraft_count=0)

    def observe_adsb_status() -> None:
        if not adsb_io_lock.acquire(blocking=False):
            return

        def observe() -> None:
            try:
                adsb_results.put((adsb.tracking, adsb.aircraft_count, None))
            finally:
                adsb_io_lock.release()

        threading.Thread(target=observe, name="orcui-adsb-status", daemon=True).start()

    def refresh_adsb_status() -> None:
        while True:
            try:
                enabled, count, error = adsb_results.get_nowait()
            except Empty:
                break
            app.set_adsb_state(enabled=enabled, aircraft_count=count)
            if error is not None:
                app.set_screen_status(error)
        observe_adsb_status()
        app.schedule_ui_callback(1000, refresh_adsb_status)

    refresh_adsb_status()
    return RadioComposition(
        screen=screen,
        directory=directory,
        favorites=favorites,
        home_factory=home_radio_factory,
        open_weather_radio=open_weather_radio,
    )
