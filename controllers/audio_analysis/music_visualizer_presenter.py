# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-neutral coordination for music visualizer behavior."""
from __future__ import annotations

from controllers.audio_analysis.music_analysis import MusicAnalyzer
from ui.music_visualizer import (
    KickMode,
    MusicVisualizerRequestHandlerIf,
    MusicVisualizerUiIf,
)


class MusicVisualizerPresenter(MusicVisualizerRequestHandlerIf):
    """Own semantic UI behavior without depending on Tk or WebUI."""

    def __init__(self, analyzer: MusicAnalyzer) -> None:
        self._analyzer = analyzer
        self._ui: MusicVisualizerUiIf | None = None
        self._kick_mode = KickMode.SINGLE
        self._lighting_enabled = False
        self.on_song_recognition_requested = None
        self.on_lighting_enabled_requested = None

    @property
    def kick_mode(self) -> KickMode:
        return self._kick_mode

    def attach_ui(self, ui: MusicVisualizerUiIf) -> None:
        self._ui = ui
        ui.set_sensitivity(self._analyzer.sensitivity)
        ui.set_zeroize_state(self._analyzer.calibrated, False)
        ui.set_lighting_enabled(self._lighting_enabled)

    def present_analysis(self, state) -> None:
        if self._ui:
            self._ui.set_analysis_state(state)
            if state.calibrated:
                self._ui.set_zeroize_state(True, False)

    def request_zeroize(self) -> None:
        self._analyzer.begin_zeroize()
        if self._ui:
            self._ui.set_zeroize_state(self._analyzer.calibrated, True)

    def request_sensitivity(self, value: float) -> None:
        self._analyzer.set_sensitivity(value)

    def request_song_recognition(self) -> None:
        if self.on_song_recognition_requested:
            self.on_song_recognition_requested()

    def request_lighting_enabled(self, enabled: bool) -> None:
        self._lighting_enabled = bool(enabled)
        if self.on_lighting_enabled_requested:
            self.on_lighting_enabled_requested(self._lighting_enabled)

    def request_kick_mode(self, mode: KickMode) -> None:
        self._kick_mode = mode
