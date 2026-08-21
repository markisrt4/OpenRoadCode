# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native Car UI music visualizer destination."""
from __future__ import annotations

import logging
import threading

from apps.carUi.screens.car_ui_screen import CarUiScreen
from apps.carUi.screens.car_ui_screen_services import MenuTileFactory
from controllers.audio_analysis.audio_analysis import AudioAnalyzer
from frontends.tk.audio_analysis import MusicVisualizerPanel
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from hardware_io.audio.pipewire_audio_capture import PipeWireAudioCapture
from ui.screen_ui_if import ScreenId

LOGGER = logging.getLogger(__name__)


class MusicVisualizerScreen(CarUiScreen):
    """Capture Linux system audio and render it using native Tk widgets."""

    def __init__(self, host: TkScreenHostIf, *, create_menu_tile: MenuTileFactory, back_action) -> None:
        super().__init__(host, ScreenId("music_visualizer"), create_menu_tile)
        self._back_action = back_action
        self._capture: PipeWireAudioCapture | None = None
        self._analyzer: AudioAnalyzer | None = None
        self._panel: MusicVisualizerPanel | None = None
        self._running = False
        self._generation = 0

    def show(self) -> None:
        self.prepare_screen("Music Visualizer", self._back_action)
        self._panel = MusicVisualizerPanel(self.content_frame)
        self._panel.pack(fill="both", expand=True)
        self._capture = PipeWireAudioCapture()
        self._analyzer = AudioAnalyzer(spectrum_band_count=24)
        try:
            self._capture.start()
        except Exception as exc:
            LOGGER.warning("System audio capture unavailable: %s", exc)
            self.set_status(f"Audio capture unavailable: {exc}")
            return
        self._running = True
        self._generation += 1
        generation = self._generation
        self.set_status("Listening to Linux system audio")
        threading.Thread(target=self._capture_loop, args=(generation,), name="carui-music-visualizer", daemon=True).start()

    def hide(self) -> None:
        self._running = False
        self._generation += 1
        capture = self._capture
        self._capture = None
        if capture is not None:
            try: capture.stop()
            except Exception: LOGGER.exception("Failed to stop visualizer capture")
        self._panel = None

    def _capture_loop(self, generation: int) -> None:
        capture, analyzer = self._capture, self._analyzer
        if capture is None or analyzer is None: return
        try:
            while self._running and generation == self._generation:
                state = analyzer.analyze(capture.read())
                self.host.schedule_ui_callback(0, lambda s=state, g=generation: self._render(g, s))
        except Exception as exc:
            LOGGER.warning("Music visualization stopped: %s", exc)
            self.host.schedule_ui_callback(0, lambda: self.set_status("Music visualization stopped"))

    def _render(self, generation: int, state) -> None:
        if generation != self._generation or not self._running or self._panel is None: return
        self._panel.update_state(state)
