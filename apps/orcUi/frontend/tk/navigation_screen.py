# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Navigation-screen lifecycle for the integrated orcUi Tk frontend."""

from __future__ import annotations

from collections.abc import Callable
import threading
from time import monotonic

from apps.orcUi.core_runtime import MapRuntimeIf
from controllers.automotive import AutomotiveTelemetryProfile
from controllers.weather.radar_palette import RadarPalette
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.navigation import (
    MapRequestHandlerIf,
    RouteRequestHandlerIf,
    RouteSimulationRequestHandlerIf,
)
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle

from .navigation_panel import NavigationPanel
from .screen_builders import build_navigation_screen


class NavigationScreen(TkScreen):
    """Own the NAVIGATION destination and its transient map presentation."""

    SCREEN_ID = ScreenId("NAVIGATION")

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        map_runtime: MapRuntimeIf,
        map_request_handler: MapRequestHandlerIf,
        route_request_handler: RouteRequestHandlerIf,
        route_simulation_handler: RouteSimulationRequestHandlerIf,
        theme_bundle: Callable[[], ThemeBundle],
        telemetry_profile_request: (
            Callable[[AutomotiveTelemetryProfile], None] | None
        ),
        on_back: Callable[[], None],
        radar_controller=None,
        radar_injection_controller=None,
        on_radar_palette_changed: Callable[[RadarPalette], None] | None = None,
        refresh_radar: Callable[[], None] | None = None,
        on_radar_visibility_changed: Callable[[], None] | None = None,
        on_radar_source_changed: Callable[[bool], None] | None = None,
        route_weather=None,
    ) -> None:
        super().__init__(self.SCREEN_ID)
        self._route_weather = route_weather
        self._host = host
        self._map_runtime = map_runtime
        self._map_request_handler = map_request_handler
        self._route_request_handler = route_request_handler
        self._route_simulation_handler = route_simulation_handler
        self._theme_bundle = theme_bundle
        self._telemetry_profile_request = telemetry_profile_request
        self._on_back = on_back
        self._radar_controller = radar_controller
        self._radar_enabled = bool(radar_controller and radar_controller.enabled)
        self._radar_injection_controller = radar_injection_controller
        self._on_radar_palette_changed = on_radar_palette_changed
        self._refresh_radar = refresh_radar
        self._on_radar_visibility_changed = on_radar_visibility_changed
        self._on_radar_source_changed = on_radar_source_changed
        self._panel: NavigationPanel | None = None
        self._radar_playing = False
        self._radar_playback_generation = 0
        self._radar_playback_speed = 1.0

    def show(self) -> None:
        """Build NAVIGATION content and start its embedded map renderer."""
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("NAVIGATION")
        self._radar_playback_speed = 1.0

        self._panel = build_navigation_screen(
            self._host.screen_parent,
            map_request_handler=self._map_request_handler,
            route_request_handler=self._route_request_handler,
            route_simulation_handler=self._route_simulation_handler,
            on_back=self._on_back,
            theme=self._theme_bundle(),
            radar_enabled=self._radar_enabled,
            radar_frame_time=(self._radar_controller.frame_time if self._radar_controller is not None else None),
            radar_palette=(self._radar_controller.palette if self._radar_controller is not None else RadarPalette.UNIVERSAL),
            on_radar_palette_changed=(self._change_radar_palette if self._radar_controller is not None else None),
            on_radar_toggle=self._toggle_radar if self._radar_controller is not None else None,
            on_radar_previous=self._radar_previous if self._radar_controller is not None else None,
            on_radar_next=self._radar_next if self._radar_controller is not None else None,
            on_radar_live=self._radar_live if self._radar_controller is not None else None,
            on_radar_play=self._radar_play_pause,
            on_radar_seek=self._radar_seek,
            on_radar_speed=self._radar_set_speed,
            on_radar_source=self._change_radar_source,
        )
        self._sync_radar_timeline()
        if self.__dict__.get("_route_weather") is not None:
            self._route_weather.attach(self._panel)

        if self._telemetry_profile_request is not None:
            self._telemetry_profile_request(AutomotiveTelemetryProfile.BACKGROUND)

        self._host.screen_parent.update_idletasks()
        self._start_map_renderer()
        if self._radar_controller is not None and self._radar_controller.enabled:
            for delay_ms in (300, 700, 1200, 2500, 5000, 10000):
                self._host.schedule_ui_callback(delay_ms, self._refresh_map_radar)

    def hide(self) -> None:
        """Stop transient navigation resources when navigating away."""
        self._pause_radar()
        if self._panel is not None:
            self._panel.close_radar_menu()
        if self.__dict__.get("_route_weather") is not None:
            self._route_weather.hide()
        self._map_runtime.stop()
        self._panel = None

    def close(self) -> None:
        """Release route forecast resources when the application exits."""
        if self.__dict__.get("_route_weather") is not None:
            self._route_weather.close()

    def _refresh_map_radar(self) -> None:
        if self._panel is not None and self._radar_controller is not None:
            if self._refresh_radar is not None:
                self._refresh_radar()
            else:
                self._radar_controller.refresh_renderer_state()

    def _start_map_renderer(self) -> None:
        panel = self._panel
        if panel is None:
            return

        try:
            self._map_runtime.launch(panel.map_host_window_id)
        except (OSError, RuntimeError) as error:
            print(
                "WARNING: map renderer: "
                f"{type(error).__name__}: {error}"
            )

    def _change_radar_palette(self, palette: RadarPalette) -> None:
        controller = self._radar_controller
        if controller is None:
            return
        controller.set_palette(palette)
        if self._on_radar_palette_changed is not None:
            self._on_radar_palette_changed(palette)

    def _select_radar_frame(self, selector: Callable[[], object]) -> None:
        def select() -> None:
            try:
                if self._radar_injection_controller is not None:
                    self._radar_injection_controller.refresh()
                frames = (None if self._radar_controller.has_frames
                          else self._radar_controller.load_frames())
                self._host.schedule_ui_callback(
                    0, lambda: self._complete_radar_selection(selector, frames)
                )
            except Exception as error:
                detail = str(error)
                self._host.schedule_ui_callback(0, lambda: self._radar_load_failed(detail))

        threading.Thread(target=select, name="weather-radar-history", daemon=True).start()

    def _complete_radar_selection(self, selector, frames) -> None:
        if not self._radar_enabled:
            return
        try:
            frame = (self._radar_controller.show_frames(frames)
                     if frames is not None else selector())
            if self._panel is not None:
                self._panel.set_radar_frame_time(frame.timestamp)
            self._sync_radar_timeline()
        except Exception as error:
            self._radar_load_failed(str(error))

    def _radar_previous(self) -> None:
        if self._radar_controller is not None:
            self._select_radar_frame(self._radar_controller.previous_frame)

    def _radar_next(self) -> None:
        if self._radar_controller is not None:
            self._select_radar_frame(self._radar_controller.next_frame)

    def _radar_live(self) -> None:
        self._pause_radar()
        if self._radar_controller is not None and self._radar_controller.is_forecast:
            self._change_radar_source(False)
            return
        if self._radar_controller is not None:
            self._toggle_radar(True)

    def _change_radar_source(self, forecast: bool) -> None:
        self._pause_radar()
        if self._on_radar_source_changed is not None:
            self._radar_controller.hide()
            self._on_radar_source_changed(forecast)
            self._sync_radar_timeline()
            self.set_radar_enabled(True)

    def _sync_radar_timeline(self) -> None:
        if self._panel is not None and self._radar_controller is not None:
            self._panel.set_radar_timeline(
                self._radar_controller.frame_times, self._radar_controller.frame_index,
                self.__dict__.get("_radar_playing", False),
                self._radar_controller.is_forecast,
            )

    def _pause_radar(self) -> None:
        self._radar_playing = False
        self._radar_playback_generation = self.__dict__.get("_radar_playback_generation", 0) + 1
        self._sync_radar_timeline()
        if self._panel is not None:
            self._panel.set_radar_loading(False)

    def _radar_seek(self, index: int) -> None:
        self._pause_radar()
        if self._radar_enabled and self._radar_controller is not None:
            try:
                self._radar_controller.select_frame(index)
                self._sync_radar_timeline()
            except (IndexError, OSError, RuntimeError) as error:
                self._radar_load_failed(str(error))

    def _radar_set_speed(self, speed: float) -> None:
        self._radar_playback_speed = speed

    def _radar_play_pause(self) -> None:
        if self._radar_playing:
            self._pause_radar()
            return
        controller = self._radar_controller
        if not self._radar_enabled or controller is None or len(controller.frame_times) < 2:
            return
        self._radar_playing = True
        self._radar_playback_generation += 1
        # Starting from Live begins the history rather than waiting at its end.
        try:
            if controller.is_live:
                controller.select_frame(0)
            self._sync_radar_timeline()
            self._queue_radar_frame(self._radar_playback_generation)
        except (IndexError, OSError, RuntimeError) as error:
            self._radar_load_failed(str(error))

    def _schedule_radar_tick(self, generation: int) -> None:
        self._host.schedule_ui_callback(
            int(1500 / self._radar_playback_speed), lambda: self._radar_tick(generation),
        )

    def _queue_radar_frame(self, generation: int) -> None:
        if not self._radar_controller.is_forecast:
            self._schedule_radar_tick(generation)
            return
        started = monotonic()
        self._host.schedule_ui_callback(100, lambda: self._wait_for_radar_tiles(generation, started))

    def _wait_for_radar_tiles(self, generation: int, started: float) -> None:
        if (not self._radar_playing or generation != self._radar_playback_generation
                or not self._radar_enabled or self._panel is None):
            return
        controller = self._radar_controller
        error = controller.frame_tile_error
        if error or monotonic() - started >= 120:
            self._pause_radar()
            self._host.set_screen_status(f"Forecast radar loading failed: {error or 'timed out waiting for map tiles'}")
            return
        ready = controller.frame_tiles_ready
        self._panel.set_radar_loading(not ready)
        if ready:
            # Start the display interval after loading, rather than counting
            # download/decode time as time spent showing the forecast.
            self._schedule_radar_tick(generation)
        else:
            self._host.schedule_ui_callback(250, lambda: self._wait_for_radar_tiles(generation, started))

    def _radar_tick(self, generation: int) -> None:
        if (not self._radar_playing or generation != self._radar_playback_generation
                or not self._radar_enabled or self._panel is None):
            return
        controller = self._radar_controller
        try:
            count = len(controller.frame_times)
            if count < 2:
                self._pause_radar()
                return
            controller.select_frame(((controller.frame_index or 0) + 1) % count)
            self._sync_radar_timeline()
            self._queue_radar_frame(generation)
        except (IndexError, OSError, RuntimeError) as error:
            self._radar_load_failed(str(error))

    def _update_radar_frame(self, panel: NavigationPanel, timestamp: int) -> None:
        if self._panel is panel:
            panel.set_radar_frame_time(timestamp)

    @property
    def radar_enabled(self) -> bool:
        """Return requested radar visibility, including pending frame loading."""
        return self._radar_enabled

    def set_radar_enabled(self, enabled: bool) -> None:
        """Set shared radar visibility from Home or Weather shortcuts."""
        panel = self._panel
        if panel is not None and panel._radar_enabled != enabled:
            panel._toggle_radar()
        else:
            self._toggle_radar(enabled)

    def _toggle_radar(self, enabled: bool) -> None:
        controller = self._radar_controller
        if controller is None:
            return
        self._radar_enabled = enabled
        generation = self.__dict__.get("_radar_load_generation", 0) + 1
        self._radar_load_generation = generation
        self._notify_radar_visibility()
        if not enabled:
            self._pause_radar()
            controller.hide()
            return

        def load_latest() -> None:
            try:
                if self._radar_injection_controller is not None:
                    self._radar_injection_controller.refresh()
                frames = controller.load_frames()
                self._host.schedule_ui_callback(0, lambda: self._show_radar_frames(frames, generation))
            except Exception as error:
                detail = str(error)
                self._host.schedule_ui_callback(0, lambda: self._radar_load_failed(detail, generation))

        threading.Thread(target=load_latest, name="weather-radar-refresh", daemon=True).start()

    def _show_radar_frames(self, frames, generation=None) -> None:
        # A completed download must not re-enable radar after the user turned it off.
        if (not self._radar_enabled or
                (generation is not None and generation != self._radar_load_generation)):
            return
        try:
            frame = self._radar_controller.show_frames(frames)
            if self._panel is not None:
                self._panel.set_radar_frame_time(frame.timestamp)
            self._sync_radar_timeline()
            # Retry through slower native startup; identical-frame replays retain tiles.
            for delay_ms in (300, 1200, 2500, 5000):
                self._host.schedule_ui_callback(delay_ms, self._replay_requested_radar)
        except Exception as error:
            self._radar_load_failed(str(error))

    def _replay_requested_radar(self) -> None:
        if self._radar_enabled and self._radar_controller is not None:
            if self._refresh_radar is not None:
                self._refresh_radar()
            else:
                self._radar_controller.refresh_renderer_state()

    def _radar_load_failed(self, detail: str, generation=None) -> None:
        if generation is not None and generation != self._radar_load_generation:
            return
        self._radar_enabled = False
        self._pause_radar()
        try:
            self._radar_controller.hide()
        except (OSError, RuntimeError):
            pass
        if self._panel is not None:
            self._panel._radar_enabled = False
            self._panel._render_radar_state()
        self._notify_radar_visibility()
        self._host.set_screen_status(f"Radar unavailable: {detail}")

    def _notify_radar_visibility(self) -> None:
        callback = self._on_radar_visibility_changed
        if callback is not None:
            callback()
