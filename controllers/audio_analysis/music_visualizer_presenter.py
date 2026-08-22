# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-neutral coordination for music visualizer behavior."""
from __future__ import annotations

from controllers.audio_analysis.music_analysis_source_if import MusicAnalysisSourceIf
from ui.music_visualizer import KickMode, MusicVisualizerRequestHandlerIf, MusicVisualizerUiIf


class MusicVisualizerPresenter(MusicVisualizerRequestHandlerIf):
    """Coordinate an abstract music-analysis source with any frontend."""

    def __init__(self, source: MusicAnalysisSourceIf) -> None:
        self._source = source
        self._ui: MusicVisualizerUiIf | None = None
        self._kick_mode = KickMode.SINGLE
        self._lighting_enabled = False
        self.on_song_recognition_requested = None
        self.on_lighting_enabled_requested = None

    @property
    def source(self) -> MusicAnalysisSourceIf:
        return self._source

    @property
    def kick_mode(self) -> KickMode:
        return self._kick_mode

    def attach_ui(self, ui: MusicVisualizerUiIf) -> None:
        self._ui = ui
        ui.set_sensitivity(self._source.sensitivity)
        ui.set_zeroize_state(self._source.calibrated, False)
        ui.set_lighting_enabled(self._lighting_enabled)

    def start(self) -> None:
        self._source.start(self.present_analysis)

    def stop(self) -> None:
        self._source.stop()

    def present_analysis(self, state) -> None:
        if self._ui:
            self._ui.set_analysis_state(state)
            if state.calibrated:
                self._ui.set_zeroize_state(True, False)

    def request_zeroize(self) -> None:
        self._source.zeroize()
        if self._ui:
            self._ui.set_zeroize_state(self._source.calibrated, True)

    def request_sensitivity(self, value: float) -> None:
        self._source.set_sensitivity(value)

    def request_song_recognition(self) -> None:
        if self.on_song_recognition_requested:
            self.on_song_recognition_requested()

    def request_lighting_enabled(self, enabled: bool) -> None:
        self._lighting_enabled = bool(enabled)
        if self.on_lighting_enabled_requested:
            self.on_lighting_enabled_requested(self._lighting_enabled)

    def request_kick_mode(self, mode: KickMode) -> None:
        self._kick_mode = mode
