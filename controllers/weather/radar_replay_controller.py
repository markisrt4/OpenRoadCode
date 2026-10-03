# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Radar replay loading and timer lifecycle outside all frontend widgets."""

from collections.abc import Callable
import math
import threading
from time import monotonic

from ui.ui_dispatcher_if import UiDispatcherIf
from ui.weather.radar_ui_if import RadarUiIf, RadarUiState, RadarPalette
from ui.weather.radar_request_handler_if import RadarRequestHandlerIf


class RadarReplayController(RadarRequestHandlerIf):
    """Own radar async work and publish immutable state to any frontend."""

    def __init__(self, dispatcher: UiDispatcherIf, ui: RadarUiIf, controller, *, injection=None,
                 on_palette=None, on_source=None, on_visibility=None, refresh_renderer=None):
        self._host, self._ui, self._radar_controller = dispatcher, ui, controller
        self._radar_injection_controller = injection
        self._on_radar_palette_changed, self._on_radar_source_changed = on_palette, on_source
        self._on_radar_visibility_changed, self._refresh_radar = on_visibility, refresh_renderer
        self._radar_enabled = bool(controller.enabled)
        self._radar_playing = self._visible = self._loading = self._closed = False
        self._radar_playback_generation = self._radar_load_generation = 0
        self._radar_playback_speed = 1.0
        self._status = ""
        self._emit()

    def request_enabled(self, enabled: bool) -> None:
        if not self._closed:
            self._toggle_radar(enabled)

    def request_previous(self) -> None:
        if self._closed:
            return
        self._radar_previous()

    def request_next(self) -> None:
        if self._closed:
            return
        self._radar_next()

    def request_live(self) -> None:
        if self._closed:
            return
        self._radar_live()

    def request_source(self, forecast: bool) -> None:
        if self._closed:
            return
        self._change_radar_source(forecast)

    def request_seek(self, index: int) -> None:
        if self._closed:
            return
        self._radar_seek(index)

    def request_play_pause(self) -> None:
        if self._closed:
            return
        if self._visible:
            self._radar_play_pause()

    def request_speed(self, speed: float) -> None:
        if self._closed:
            return
        if not math.isfinite(speed) or speed <= 0:
            raise ValueError("Radar replay speed must be positive")
        self._radar_set_speed(speed)
        self._emit()

    def request_palette(self, palette: RadarPalette) -> None:
        if self._closed:
            return
        self._change_radar_palette(palette)
        self._emit()

    def request_navigation_visible(self, visible: bool) -> None:
        if self._closed:
            return
        self._visible = visible
        if not visible:
            self._pause_radar()
        self._emit()

    def request_replay(self) -> None:
        self._replay_requested_radar()

    def close(self):
        """Invalidate outstanding callbacks without taking ownership of provider resources."""
        self._pause_radar()
        self._closed = True
        self._radar_load_generation += 1

    def _set_status(self, status):
        self._status = status
        self._emit()

    def _emit(self):
        if self._closed:
            return
        controller = self._radar_controller
        self._ui.set_radar_state(RadarUiState(
            self._radar_enabled, controller.frame_time, tuple(controller.frame_times), controller.frame_index,
            self._radar_playing, controller.is_forecast, self._loading, self._radar_playback_speed,
            controller.palette, self._status))

    def _change_radar_palette(self, palette: RadarPalette) -> None:
        controller = self._radar_controller
        if controller is None:
            return
        controller.set_palette(palette)
        if self._on_radar_palette_changed is not None:
            self._on_radar_palette_changed(palette)

    def _select_radar_frame(self, selector: Callable[[], object]) -> None:
        self._radar_load_generation += 1
        generation = self._radar_load_generation
        def select() -> None:
            try:
                if self._radar_injection_controller is not None:
                    self._radar_injection_controller.refresh()
                frames = (None if self._radar_controller.has_frames
                          else self._radar_controller.load_frames())
                self._host.schedule_ui_callback(
                    0, lambda: self._complete_radar_selection(selector, frames, generation)
                )
            except Exception as error:
                detail = str(error)
                self._host.schedule_ui_callback(0, lambda: self._radar_load_failed(detail, generation))

        threading.Thread(target=select, name="weather-radar-history", daemon=True).start()

    def _complete_radar_selection(self, selector, frames, generation=None) -> None:
        if self._closed or not self._radar_enabled or (generation is not None and generation != self._radar_load_generation):
            return
        try:
            frame = (self._radar_controller.show_frames(frames)
                     if frames is not None else selector())
            if self._visible:
                self._emit()
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
            self._toggle_radar(True)

    def _sync_radar_timeline(self) -> None:
        self._emit()

    def _pause_radar(self) -> None:
        self._radar_playing = False
        self._radar_playback_generation = self.__dict__.get("_radar_playback_generation", 0) + 1
        self._sync_radar_timeline()
        if self._visible:
            self._loading = False
            self._emit()

    def _radar_seek(self, index: int) -> None:
        self._pause_radar()
        if not self._closed and self._radar_enabled and self._radar_controller is not None:
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
                or not self._radar_enabled or not self._visible):
            return
        controller = self._radar_controller
        error = controller.frame_tile_error
        if error or monotonic() - started >= 120:
            self._pause_radar()
            self._set_status(f"Forecast radar loading failed: {error or 'timed out waiting for map tiles'}")
            return
        ready = controller.frame_tiles_ready
        self._loading = not ready
        self._emit()
        if ready:
            # Start the display interval after loading, rather than counting
            # download/decode time as time spent showing the forecast.
            self._schedule_radar_tick(generation)
        else:
            self._host.schedule_ui_callback(250, lambda: self._wait_for_radar_tiles(generation, started))

    def _radar_tick(self, generation: int) -> None:
        if (not self._radar_playing or generation != self._radar_playback_generation
                or not self._radar_enabled or not self._visible):
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

    def _toggle_radar(self, enabled: bool) -> None:
        controller = self._radar_controller
        if controller is None:
            return
        self._radar_enabled = enabled
        self._status = ""
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
        if (self._closed or not self._radar_enabled or
                (generation is not None and generation != self._radar_load_generation)):
            return
        try:
            frame = self._radar_controller.show_frames(frames)
            if self._visible:
                self._emit()
            self._sync_radar_timeline()
            # Retry through slower native startup; identical-frame replays retain tiles.
            for delay_ms in (300, 1200, 2500, 5000):
                self._host.schedule_ui_callback(delay_ms, self._replay_requested_radar)
        except Exception as error:
            self._radar_load_failed(str(error))

    def _replay_requested_radar(self) -> None:
        if not self._closed and self._radar_enabled and self._radar_controller is not None:
            if self._refresh_radar is not None:
                self._refresh_radar()
            else:
                self._radar_controller.refresh_renderer_state()

    def _radar_load_failed(self, detail: str, generation=None) -> None:
        if self._closed or (generation is not None and generation != self._radar_load_generation):
            return
        self._radar_enabled = False
        self._pause_radar()
        try:
            self._radar_controller.hide()
        except (OSError, RuntimeError):
            pass
        self._notify_radar_visibility()
        self._set_status(f"Radar unavailable: {detail}")

    def _notify_radar_visibility(self) -> None:
        self._emit()
        callback = self._on_radar_visibility_changed
        if callback is not None:
            callback()
