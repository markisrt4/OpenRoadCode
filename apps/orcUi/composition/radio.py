# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose radio presentation and feature-scoped dependencies."""

from __future__ import annotations

import logging
import os
import threading
import tkinter as tk
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from queue import Empty, SimpleQueue

from apps.orcUi.adapters.adsb_control import OrcUiAdsbControl
from apps.orcUi.application_runtime import OrcUiApplicationRuntime
from apps.orcUi.composition.radio_resources import (
    RadioComposition,
    StreamingRadioResources,
)
from apps.orcUi.composition.rf_receivers import ManagedReceiverServices
from apps.orcUi.composition.trending_radio import configure_trending
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.frontend.tk.radio_entry_panel import RadioEntryPanel
from apps.orcUi.frontend.tk.radio_panel import RadioPanel
from apps.orcUi.theme_runtime import theme_bundle
from common.resource_cleanup import ResourceCleanup
from controllers.radio.adapters.radio_browser_directory import RadioBrowserDirectory
from controllers.radio.adapters.sdrforge_rest_radio_backend import SdrForgeRestRadioBackend
from controllers.radio.adapters.sdrforge_zmq_spectrum_adapter import SdrForgeTelemetrySubscriber
from controllers.radio.native_radio_control import NativeRadioControl
from controllers.radio.radio_profile_controller import RadioProfileController
from controllers.radio.receiver_assignments import ReceiverAssignmentStore
from controllers.radio.receiver_ownership import ReceiverOwnershipController
from controllers.radio.receiver_settings_controller import ReceiverSettingsController
from controllers.radio.rf_radio_session import ReceiverSession
from controllers.radio.streaming_radio_artwork import download_station_artwork
from controllers.radio.streaming_radio_browser import StreamingRadioBrowser
from controllers.radio.streaming_radio_favorites import StreamingRadioFavorites
from controllers.radio.weather_radio import play_weather_radio
from frontends.tk.radio import RadioScreen
from frontends.tk.radio.persistent_streaming_radio_panel import PersistentStreamingRadioPanel
from frontends.tk.radio.streaming_radio_now_playing import StreamingRadioNowPlaying
from frontends.x11.x11_window_embedder import X11WindowEmbedder
from hardware_io.rf.linux_usb_receiver_adapter import LinuxUsbReceiverAdapter
from protocols.rigctl.rigctl_client import RigctlClient
from protocols.sdrforge_control import authorize_local_sdrforge_request
from ui.radio import AircraftMenuRequestHandlerIf
from ui.radio.radio_visualization_config import (
    RadioRenderer,
    RadioVisualizationConfig,
    RadioVisualizationSettingsIf,
)
from ui.theme import ThemeBundle, ThemeMode


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


def stop_sdrforge_receiver() -> None:
    """Release RF acquisition at application shutdown, not screen retirement."""
    try:
        with urllib.request.urlopen(
            authorize_local_sdrforge_request(
                urllib.request.Request(
                    "http://127.0.0.1:5570/v1/receiver/stop",
                    data=b"",
                    method="POST",
                )
            ),
            timeout=5.0,
        ):
            pass
    except (OSError, RuntimeError) as exc:
        logging.getLogger(__name__).debug("SDRForge shutdown: %s", exc)


def configure_radio(
    app: OrcUiApp,
    runtime: OrcUiApplicationRuntime,
    visualization_settings: RadioVisualizationSettingsIf | None = None,
) -> RadioComposition:
    """Compose radio UI against runtime-owned playback and SDR services."""

    with ResourceCleanup() as cleanup:
        rigctl_client = RigctlClient()
        token = os.environ.get("SDRFORGE_ACQUISITION_TOKEN")

        def sync_theme(mode: ThemeMode) -> None:
            """Native radio widgets consume the ORC theme directly."""
            del mode

        resources = StreamingRadioResources(
            app.cancel_ui_callback,
            stop_receiver=stop_sdrforge_receiver,
        )
        cleanup.callback(resources.close)
        ownership = ReceiverOwnershipController()
        assignments = ReceiverAssignmentStore()
        discovery = LinuxUsbReceiverAdapter()
        managed = (
            ManagedReceiverServices(token, ownership, assignments, discovery) if token else None
        )
        if managed is not None:
            resources.stop_receiver = managed.close
        managed_backend = (
            SdrForgeRestRadioBackend(
                shared_receiver=True, before_mutation=managed.guard_radio_control
            )
            if managed is not None
            else None
        )
        receiver_settings = (
            None
            if not os.path.isdir("/sys/bus/usb/devices")
            else ReceiverSettingsController(
                discovery,
                assignments,
                ownership,
                acquisition=managed.acquisition if managed is not None else None,
                run_work=resources.run_work,
                run_ui=app.dispatch_ui,
            )
        )
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
                        app.dispatch_ui(
                            lambda: app.set_screen_status(message) if not resources.closed else None
                        )

                resources.run_work(stop_offline)

        if online_mode is not None:
            resources.unsubscribe = online_mode.subscribe(mode_changed)
        mode_changed(network_allowed())
        directory = RadioBrowserDirectory(timeout_s=10.0, network_allowed=network_allowed)
        favorites = StreamingRadioFavorites()
        adsb_enabled = os.environ.get("ORC_NO_ADSB") != "1"
        adsb = (
            OrcUiAdsbControl(
                set_managed_tracking=managed.set_adsb_tracking,
                managed_tracking=managed.adsb_active,
            )
            if managed is not None
            else OrcUiAdsbControl()
        )

        def load_artwork(url: str) -> bytes:
            if not network_allowed():
                raise RuntimeError("Internet radio artwork unavailable in offline mode")
            return download_station_artwork(url)

        def streaming_panel_factory(
            parent: tk.Misc,
            theme: ThemeBundle,
            on_back: Callable[[], None],
        ) -> PersistentStreamingRadioPanel:
            if resources.closed:
                raise RuntimeError("Radio composition is closed")
            session = StreamingRadioBrowser(
                directory,
                runtime.streaming_radio,
                favorites,
                run_work=resources.run_work,
                run_ui=app.dispatch_ui,
                load_artwork=load_artwork,
                on_close=lambda: resources.sessions.discard(session),
                run_artwork=resources.run_artwork,
            )
            with ResourceCleanup() as rollback:
                rollback.callback(session.close)
                panel = PersistentStreamingRadioPanel(
                    parent,
                    session=session,
                    theme=theme,
                    on_back=on_back,
                )
                resources.sessions.add(session)
                rollback.release()
            return panel

        trending = configure_trending(
            register_cleanup=cleanup.callback,
            dispatch_ui=app.dispatch_ui,
            run_work=resources.run_work,
            network_allowed=network_allowed,
            closed=lambda: resources.closed,
            notification_sink=app.notification_sink,
        )

        def rf_panel_factory(
            parent: tk.Misc, theme: ThemeBundle, *, fm_only: bool = False
        ) -> RadioPanel:
            if resources.closed:
                raise RuntimeError("Radio composition is closed")
            radio = RadioProfileController(client=rigctl_client, backend=managed_backend)
            visualization = RadioVisualizationConfig(
                renderer=RadioRenderer(os.environ.get("ORC_RADIO_RENDERER", "auto").lower()),
                waterfall_rows=int(os.environ.get("ORC_RADIO_WATERFALL_ROWS", "180")),
                max_fps=int(os.environ.get("ORC_RADIO_MAX_FPS", "10")),
                palette=os.environ.get("ORC_RADIO_PALETTE", "classic").lower(),
            )
            if visualization_settings is not None:
                visualization = visualization_settings.load(visualization)
            if os.environ.get("ORC_NO_OPENGL") == "1":
                visualization = RadioVisualizationConfig(
                    renderer=RadioRenderer.TK,
                    waterfall_rows=visualization.waterfall_rows,
                    max_fps=visualization.max_fps,
                    palette=visualization.palette,
                )
            source = SdrForgeTelemetrySubscriber(
                os.environ.get("SDRFORGE_ZMQ_ENDPOINT", "tcp://127.0.0.1:5571")
            )
            display_control = NativeRadioControl()
            session = ReceiverSession(
                radio,
                display_control,
                runtime.radio,
                adsb,
                X11WindowEmbedder(),
                display=os.environ.get("DISPLAY", ":1"),
                run_work=resources.run_rf,
                run_ui=app.dispatch_ui,
                on_close=lambda: resources.rf_sessions.discard(session),
                spectrum_source=source,
                notification_sink=app.notification_sink,
                start_receiver=managed.start_radio if managed is not None else None,
                stop_receiver=managed.stop_radio if managed is not None else None,
                guard_receiver_control=managed.guard_radio_control if managed is not None else None,
            )
            with ResourceCleanup() as rollback:
                rollback.callback(session.close)
                resources.rf_sessions.add(session)
                panel = RadioPanel(
                    parent,
                    session=session,
                    theme=theme,
                    native_sdrforge=True,
                    visualization=visualization,
                    fm_only=fm_only,
                )
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
                trending_panel_factory=trending.panel_factory,
                on_location_changed=lambda leaf: app.set_breadcrumb("RADIO", leaf),
            ),
            sync_theme=sync_theme,
            on_location_changed=lambda leaf: app.set_breadcrumb("RADIO", leaf),
        )
        app.register_screen("RADIO", screen)

        def show_radio_source(source: str) -> None:
            """Navigate through the shell before opening a radio source."""
            if source == "adsb" and not adsb_enabled:
                app.set_screen_status("ADS-B intentionally disabled")
                return
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
                    weather_backend = (
                        SdrForgeRestRadioBackend(managed.start_weather(), shared_receiver=True)
                        if managed is not None
                        else managed_backend
                    )
                    state = play_weather_radio(
                        RadioProfileController(backend=weather_backend),
                        runtime.radio,
                        cancelled=lambda: resources.closed,
                        native_sdrforge=managed is None,
                    )
                    if state is None:
                        logger.info("NOAA request cancelled")
                        return
                    message = (
                        f"RF: Playing {state.frequency_hz / 1_000_000:.3f} MHz · {state.label}"
                    )
                    logger.info("NOAA tuned: %s", message)
                except Exception as error:
                    logger.exception("NOAA request failed")
                    message = f"RF: {error}"
                app.dispatch_ui(
                    lambda: app.set_screen_status(message) if not resources.closed else None
                )

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
                if enabled and managed is None and runtime.radio.presented:
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
            if not adsb_enabled:
                app.set_screen_status("ADS-B intentionally disabled")
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

        app.set_aircraft_request_handler(
            AircraftMenuRequests(
                toggle_adsb=request_adsb,
                open_tracker=lambda: show_radio_source("adsb"),
                open_airband=lambda: show_radio_source("airband"),
            )
        )
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
                app.set_adsb_state(
                    enabled=enabled, aircraft_count=count, simulation=adsb.simulation
                )
                if error is not None:
                    app.set_screen_status(error)
            observe_adsb_status()
            resources.adsb_callback = app.schedule_ui_callback(1000, refresh_adsb_status)

        if adsb_enabled:
            refresh_adsb_status()
        composition = RadioComposition(
            screen=screen,
            directory=directory,
            favorites=favorites,
            home_factory=home_radio_factory,
            open_weather_radio=open_weather_radio,
            streaming_resources=resources,
            bind_song_launch=trending.bind_song_launch,
            close_charts=trending.close_charts,
            bind_video_player=trending.bind_video_player,
            bind_spotify_factory=trending.bind_spotify_factory,
            rigctl_client=rigctl_client,
            receiver_settings=receiver_settings,
        )
        cleanup.release()
    return composition
