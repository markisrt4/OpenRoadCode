# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose radio presentation and feature-scoped dependencies."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

from apps.orcUi.application_runtime import OrcUiApplicationRuntime
from common.resource_cleanup import ResourceCleanup, close_resources

from apps.launchers.sdrpp_launcher import sync_sdrpp_theme
from apps.orcUi.adapters.adsb_control import OrcUiAdsbControl
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.frontend.tk.radio_entry_panel import RadioEntryPanel
from apps.orcUi.theme_runtime import theme_bundle
from controllers.radio.adapters.radio_browser_directory import RadioBrowserDirectory
from controllers.radio.radio_profile_controller import RadioProfileController
from controllers.radio.streaming_radio_favorites import StreamingRadioFavorites
from controllers.radio.streaming_radio_browser import StreamingRadioBrowser
from controllers.radio.streaming_radio_artwork import download_station_artwork
from frontends.tk.radio.persistent_streaming_radio_panel import PersistentStreamingRadioPanel
from frontends.x11.x11_window_embedder import X11WindowEmbedder
from frontends.tk.radio import RadioScreen
from frontends.tk.radio.streaming_radio_now_playing import StreamingRadioNowPlaying
from ui.theme import ThemeBundle, ThemeMode


@dataclass(slots=True)
class StreamingRadioResources:
    """Retain worker and browser ownership independently of widget lifetime."""

    cancel_callback: Callable[[object], None]
    executor: ThreadPoolExecutor = field(default_factory=lambda: ThreadPoolExecutor(
        max_workers=4, thread_name_prefix="orcui-streaming-radio",
    ))
    artwork_executor: ThreadPoolExecutor = field(default_factory=lambda: ThreadPoolExecutor(
        max_workers=4, thread_name_prefix="orcui-radio-artwork",
    ))
    sessions: set[StreamingRadioBrowser] = field(default_factory=set)
    unsubscribe: Callable[[], None] = lambda: None
    adsb_callback: object | None = None
    closed: bool = False

    def run_work(self, work: Callable[[], None]) -> None:
        if not self.closed:
            self.executor.submit(work)

    def run_artwork(self, work: Callable[[], None]) -> None:
        if not self.closed:
            self.artwork_executor.submit(work)

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        def cancel_adsb() -> None:
            if self.adsb_callback is not None:
                self.cancel_callback(self.adsb_callback)
                self.adsb_callback = None
        close_resources(
            self.unsubscribe, cancel_adsb,
            *(session.close for session in tuple(self.sessions)),
            lambda: self.executor.shutdown(wait=False, cancel_futures=True),
            lambda: self.artwork_executor.shutdown(wait=False, cancel_futures=True),
        )


@dataclass(slots=True)
class RadioComposition:
    """Own radio presentation resources created by the composition root."""

    screen: RadioScreen
    directory: RadioBrowserDirectory
    favorites: StreamingRadioFavorites
    home_factory: Callable[[tk.Misc], tk.Widget]
    open_weather_radio: Callable[[], None]
    streaming_resources: StreamingRadioResources

    def close(self) -> None:
        """Retire browser sessions and workers; runtime retains playback ownership."""
        self.streaming_resources.close()


def configure_radio(app: OrcUiApp, runtime: OrcUiApplicationRuntime) -> RadioComposition:
    """Compose radio UI against runtime-owned playback and SDR services."""

    with ResourceCleanup() as cleanup:
        def sync_theme(mode: ThemeMode) -> None:
            sync_sdrpp_theme("Light" if mode is ThemeMode.LIGHT else "Dark")

        resources = StreamingRadioResources(app.cancel_ui_callback)
        cleanup.callback(resources.close)
        online_mode = app.online_mode
        def network_allowed() -> bool:
            return online_mode is None or online_mode.online
        runtime.streaming_radio.set_network_allowed(network_allowed)
        def mode_changed(online: bool) -> None:
            if not online:
                def stop_offline() -> None:
                    try:
                        runtime.streaming_radio.stop_if_offline()
                    except (OSError, RuntimeError) as exc:
                        message = f"Could not stop internet radio: {exc}"
                        app.dispatch_ui(lambda: app.set_screen_status(message) if not resources.closed else None)
                resources.run_work(stop_offline)
        if online_mode is not None:
            resources.unsubscribe = online_mode.subscribe(mode_changed)
        mode_changed(network_allowed())
        directory = RadioBrowserDirectory(timeout_s=10.0, network_allowed=network_allowed)
        favorites = StreamingRadioFavorites()
        adsb = OrcUiAdsbControl()

        def load_artwork(url: str) -> bytes:
            if not network_allowed():
                raise RuntimeError("Internet radio artwork unavailable in offline mode")
            return download_station_artwork(url)

        def streaming_panel_factory(
            parent: tk.Misc, theme: ThemeBundle, on_back: Callable[[], None],
        ) -> PersistentStreamingRadioPanel:
            if resources.closed:
                raise RuntimeError("Radio composition is closed")
            session = StreamingRadioBrowser(
                directory, runtime.streaming_radio, favorites, run_work=resources.run_work,
                run_ui=app.dispatch_ui, load_artwork=load_artwork,
                on_close=lambda: resources.sessions.discard(session),
                run_artwork=resources.run_artwork,
            )
            with ResourceCleanup() as rollback:
                rollback.callback(session.close)
                panel = PersistentStreamingRadioPanel(
                    parent, session=session, theme=theme, on_back=on_back,
                )
                resources.sessions.add(session)
                rollback.release()
            return panel

        screen = RadioScreen(
            app,
            embedder=X11WindowEmbedder(),
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            theme_mode=lambda: app.theme_mode,
            panel_factory=lambda parent, embedder, theme: RadioEntryPanel(
                parent,
                embedder=embedder,
                theme=theme,
                radio_application=runtime.radio,
                online_mode=app.online_mode,
                streaming_panel_factory=streaming_panel_factory,
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

        def home_radio_factory(parent: tk.Misc) -> tk.Widget:
            return StreamingRadioNowPlaying(
                parent,
                state_source=runtime.streaming_radio,
                online_allowed=network_allowed,
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
            if resources.closed:
                return
            app.set_adsb_state(enabled=adsb.tracking, aircraft_count=adsb.aircraft_count)
            resources.adsb_callback = app.schedule_ui_callback(1000, refresh_adsb_status)

        resources.adsb_callback = app.schedule_ui_callback(1000, refresh_adsb_status)
        composition = RadioComposition(
            screen=screen,
            directory=directory,
            favorites=favorites,
            home_factory=home_radio_factory,
            open_weather_radio=open_weather_radio,
            streaming_resources=resources,
        )
        cleanup.release()
    return composition
