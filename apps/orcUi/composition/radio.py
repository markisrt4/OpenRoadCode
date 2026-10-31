# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose radio presentation and feature-scoped dependencies."""

from __future__ import annotations

import os
import logging
import tkinter as tk
import threading
from queue import Empty, SimpleQueue
from collections.abc import Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

from apps.orcUi.application_runtime import OrcUiApplicationRuntime
from common.resource_cleanup import ResourceCleanup, close_resources

from apps.launchers.sdrpp_launcher import sync_sdrpp_theme
from apps.orcUi.adapters.adsb_control import OrcUiAdsbControl
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.frontend.tk.radio_entry_panel import RadioEntryPanel
from apps.orcUi.frontend.tk.trending_radio_panel import TrendingRadioPanel
from apps.orcUi.adapters.musicforge_api_adapter import MusicForgeApiAdapter
from ui.media.song_launch import SongLaunchRequest
from apps.orcUi.adapters.managed_browser_media_player import ManagedBrowserMediaPlayer
from apps.orcUi.theme_runtime import theme_bundle
from controllers.radio.adapters.radio_browser_directory import RadioBrowserDirectory
from controllers.radio.weather_radio import play_weather_radio
from controllers.radio.rf_radio_session import ReceiverSession
from controllers.sdr.sdrpp_control import SDRPPControl
from controllers.sdr.sdr_telemetry_monitor import SDRTelemetryMonitor
from apps.orcUi.frontend.tk.radio_panel import RadioPanel
from controllers.radio.radio_profile_controller import RadioProfileController
from controllers.radio.streaming_radio_favorites import StreamingRadioFavorites
from controllers.radio.streaming_radio_browser import StreamingRadioBrowser
from controllers.radio.streaming_radio_artwork import download_station_artwork
from frontends.tk.radio.persistent_streaming_radio_panel import PersistentStreamingRadioPanel
from frontends.x11.x11_window_embedder import X11WindowEmbedder
from frontends.tk.radio import RadioScreen
from frontends.tk.radio.streaming_radio_now_playing import StreamingRadioNowPlaying
from ui.theme import ThemeBundle, ThemeMode


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
class StreamingRadioResources:
    """Retain worker and browser ownership independently of widget lifetime."""

    cancel_callback: Callable[[object], None]
    executor: ThreadPoolExecutor = field(default_factory=lambda: ThreadPoolExecutor(
        max_workers=4, thread_name_prefix="orcui-streaming-radio",
    ))
    artwork_executor: ThreadPoolExecutor = field(default_factory=lambda: ThreadPoolExecutor(
        max_workers=4, thread_name_prefix="orcui-radio-artwork",
    ))
    rf_executor: ThreadPoolExecutor = field(default_factory=lambda: ThreadPoolExecutor(
        max_workers=1, thread_name_prefix="orcui-rf-radio",
    ))
    rf_sessions: set[ReceiverSession] = field(default_factory=set)
    sessions: set[StreamingRadioBrowser] = field(default_factory=set)
    unsubscribe: Callable[[], None] = lambda: None
    adsb_callback: object | None = None
    closed: bool = False

    def run_work(self, work: Callable[[], None]) -> None:
        if not self.closed:
            self.executor.submit(work)

    def run_rf(self, work: Callable[[], None]) -> None:
        if not self.closed:
            self.rf_executor.submit(work)

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
            *(session.close for session in tuple(self.rf_sessions)),
            lambda: self.rf_executor.shutdown(wait=False, cancel_futures=False),
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
    bind_song_launch: Callable[[Callable[[SongLaunchRequest], None]], None] = lambda _handler: None
    close_charts: Callable[[], None] = lambda: None
    bind_video_player: Callable[[ManagedBrowserMediaPlayer], None] = lambda _player: None
    bind_spotify_factory: Callable[[Callable], None] = lambda _factory: None

    def close(self) -> None:
        """Retire browser sessions and workers; runtime retains playback ownership."""
        self.streaming_resources.close()
        self.close_charts()


def configure_radio(app: OrcUiApp, runtime: OrcUiApplicationRuntime) -> RadioComposition:
    """Compose radio UI against runtime-owned playback and SDR services."""

    with ResourceCleanup() as cleanup:
        def sync_theme(mode: ThemeMode) -> None:
            def work() -> None:
                sync_sdrpp_theme("Light" if mode is ThemeMode.LIGHT else "Dark")
            resources.run_rf(work)

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
        charts = MusicForgeApiAdapter(os.getenv("MUSICFORGE_AIRPLAY_URL", "http://127.0.0.1:8000"))
        cleanup.callback(charts.close)
        song_launch: list[Callable[[SongLaunchRequest], None]] = []
        video_players: list[ManagedBrowserMediaPlayer] = []
        spotify_factories: list[Callable] = []

        def bind_spotify_factory(factory: Callable) -> None:
            spotify_factories[:] = [factory]

        def bind_video_player(player: ManagedBrowserMediaPlayer) -> None:
            video_players[:] = [player]

        def bind_song_launch(handler: Callable[[SongLaunchRequest], None]) -> None:
            song_launch[:] = [handler]

        def trending_panel_factory(parent: tk.Misc, theme: ThemeBundle,
                                   on_back: Callable[[], None]) -> TrendingRadioPanel:
            generation = [0]
            panel: TrendingRadioPanel

            def refresh(station: str, period: str, kind: str = 'songs') -> None:
                generation[0] += 1
                request = generation[0]
                if not network_allowed():
                    panel.set_error("Offline mode")
                    return

                def work() -> None:
                    try:
                        stations = charts.stations()
                        chart = (charts.artists if kind == 'artists' else charts.songs)(
                            station=None if station == "All stations" else station,
                            period=period, limit=40,
                        )
                        error = None
                    except Exception as exc:
                        stations, chart, error = [], {}, str(exc)

                    def deliver() -> None:
                        if resources.closed or request != generation[0] or not panel.winfo_exists():
                            return
                        if error is not None:
                            panel.set_error(error)
                        else:
                            panel.set_stations(stations)
                            panel.set_chart(chart, kind=kind)

                    app.dispatch_ui(deliver)

                resources.run_work(work)

            def play(request: SongLaunchRequest) -> None:
                if not song_launch:
                    app.set_screen_status("YouTube search not configured")
                    return
                song_launch[0](request)

            panel = TrendingRadioPanel(parent, theme=theme, on_back=on_back,
                                       on_refresh=refresh, on_play=play,
                                       radio_factory=lambda host, colors: rf_panel_factory(host, colors, fm_only=True),
                                       video_player=lambda: video_players[0] if video_players else None,
                                       spotify_factory=lambda host, back: spotify_factories[0](host, back) if spotify_factories else None)
            return panel

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

        def rf_panel_factory(parent: tk.Misc, theme: ThemeBundle, *, fm_only: bool = False) -> RadioPanel:
            if resources.closed:
                raise RuntimeError("Radio composition is closed")
            radio = RadioProfileController()
            session = ReceiverSession(
                radio, SDRPPControl(), SDRTelemetryMonitor(radio), runtime.radio,
                adsb, X11WindowEmbedder(), display=os.environ.get("DISPLAY", ":1"),
                run_work=resources.run_rf, run_ui=app.dispatch_ui,
                on_close=lambda: resources.rf_sessions.discard(session),
            )
            with ResourceCleanup() as rollback:
                rollback.callback(session.close)
                resources.rf_sessions.add(session)
                panel = RadioPanel(parent, session=session, theme=theme, fm_only=fm_only)
                rollback.release()
            return panel

        screen = RadioScreen(
            app,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            theme_mode=lambda: app.theme_mode,
            panel_factory=lambda parent, theme: RadioEntryPanel(
                parent,
                theme=theme,
                rf_panel_factory=rf_panel_factory,
                online_mode=app.online_mode,
                streaming_panel_factory=streaming_panel_factory,
                trending_panel_factory=trending_panel_factory,
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
            logger = logging.getLogger("orc.radio.noaa")
            if resources.closed:
                logger.warning("NOAA request ignored: radio composition is closed")
                return
            logger.info("NOAA request queued")
            app.set_screen_status("RF: starting NOAA Weather Radio")
            def work() -> None:
                if resources.closed:
                    return
                logger.info("NOAA worker started")
                try:
                    state = play_weather_radio(RadioProfileController(), runtime.radio,
                                               cancelled=lambda: resources.closed)
                    if state is None:
                        logger.info("NOAA request cancelled")
                        return
                    message = f"RF: Playing {state.frequency_hz / 1_000_000:.3f} MHz · {state.label}"
                    logger.info("NOAA tuned: %s", message)
                except Exception as error:
                    logger.exception("NOAA request failed")
                    message = f"RF: {error}"
                app.dispatch_ui(lambda: app.set_screen_status(message) if not resources.closed else None)
            resources.run_rf(work)

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
            if resources.closed:
                return
            if not adsb_io_lock.acquire(blocking=False):
                return

            def apply() -> None:
                try:
                    effective, error = toggle_adsb(enabled)
                    adsb_results.put((effective, adsb.aircraft_count, error))
                finally:
                    adsb_io_lock.release()

            resources.run_rf(apply)

        app.set_aircraft_request_handler(AircraftMenuRequests(
            toggle_adsb=request_adsb,
            open_tracker=lambda: show_radio_source("adsb"),
            open_airband=lambda: show_radio_source("airband"),
        ))
        app.set_adsb_state(enabled=False, aircraft_count=0, simulation=adsb.simulation)

        def observe_adsb_status() -> None:
            if not adsb_io_lock.acquire(blocking=False):
                return

            def observe() -> None:
                try:
                    adsb_results.put((adsb.tracking, adsb.aircraft_count, None))
                finally:
                    adsb_io_lock.release()

            resources.run_rf(observe)

        def refresh_adsb_status() -> None:
            if resources.closed:
                return
            while True:
                try:
                    enabled, count, error = adsb_results.get_nowait()
                except Empty:
                    break
                app.set_adsb_state(enabled=enabled, aircraft_count=count, simulation=adsb.simulation)
                if error is not None:
                    app.set_screen_status(error)
            observe_adsb_status()
            resources.adsb_callback = app.schedule_ui_callback(1000, refresh_adsb_status)

        refresh_adsb_status()
        composition = RadioComposition(
            screen=screen,
            directory=directory,
            favorites=favorites,
            home_factory=home_radio_factory,
            open_weather_radio=open_weather_radio,
            streaming_resources=resources,
            bind_song_launch=bind_song_launch,
            close_charts=charts.close,
            bind_video_player=bind_video_player,
        )
        cleanup.release()
    return composition
