# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-neutral coordination for music visualizer behavior."""
from __future__ import annotations

from collections.abc import Callable

from controllers.audio_analysis.music_analysis_source_if import MusicAnalysisSourceIf
from controllers.music_lighting import MusicLightingController
from controllers.song_recognition import SongRecognitionController, SongRecognitionResult
from ui.music_visualizer import (
    KickMode,
    MusicVisualizationMode,
    MusicVisualizerRequestHandlerIf,
    MusicVisualizerUiIf,
    SongRecognitionUiState,
)


class MusicVisualizerPresenter(MusicVisualizerRequestHandlerIf):
    """Coordinate music-analysis and recognition services with any frontend."""

    def __init__(
        self,
        source: MusicAnalysisSourceIf,
        song_recognition: SongRecognitionController,
        *,
        music_lighting: MusicLightingController | None = None,
        dispatch: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        self._source = source
        self._song_recognition = song_recognition
        self._music_lighting = music_lighting
        self._dispatch = dispatch or (lambda callback: callback())
        self._ui: MusicVisualizerUiIf | None = None
        self._kick_mode = KickMode.SINGLE
        self._visualization_mode = MusicVisualizationMode.SPECTRUM

    @property
    def source(self) -> MusicAnalysisSourceIf:
        return self._source

    def attach_ui(self, ui: MusicVisualizerUiIf) -> None:
        self._ui = ui
        ui.set_sensitivity(self._source.sensitivity)
        ui.set_zeroize_state(self._source.calibrated, False)
        ui.set_visualization_mode(self._visualization_mode)
        ui.set_song_recognition_state(
            SongRecognitionUiState(
                configured=self._song_recognition.is_configured,
                provider=self._song_recognition.provider_name,
            )
        )

    def start(self) -> None:
        self._source.start(self.present_analysis)

    def stop(self) -> None:
        self._source.stop()

    def present_analysis(self, state) -> None:
        if self._music_lighting:
            self._music_lighting.update_analysis(state)
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
        if not self._song_recognition.is_configured:
            if self._ui:
                self._ui.set_song_recognition_state(SongRecognitionUiState(configured=False))
            return
        if self._ui:
            self._ui.set_song_recognition_state(
                SongRecognitionUiState(
                    configured=True,
                    recognizing=True,
                    provider=self._song_recognition.provider_name,
                )
            )
        started = self._song_recognition.identify_async(self._recognition_result, self._recognition_error)
        if not started and self._ui:
            self._ui.set_song_recognition_state(
                SongRecognitionUiState(configured=True, recognizing=False, provider=self._song_recognition.provider_name)
            )

    def _recognition_result(self, result: SongRecognitionResult | None) -> None:
        self._dispatch(lambda: self._present_recognition_result(result))

    def _present_recognition_result(self, result: SongRecognitionResult | None) -> None:
        if self._ui:
            self._ui.set_song(result)
            self._ui.set_song_recognition_state(
                SongRecognitionUiState(configured=self._song_recognition.is_configured, provider=self._song_recognition.provider_name)
            )

    def _recognition_error(self, message: str) -> None:
        self._dispatch(lambda: self._present_recognition_error(message))

    def _present_recognition_error(self, message: str) -> None:
        if self._ui:
            self._ui.set_status(f"Recognition failed: {message}")
            self._ui.set_song_recognition_state(
                SongRecognitionUiState(configured=self._song_recognition.is_configured, provider=self._song_recognition.provider_name)
            )

    def request_lighting_enabled(self, enabled: bool) -> None:
        """Compatibility bridge; lighting owns its own contract/state."""
        if self._music_lighting:
            self._music_lighting.request_enabled(enabled)

    def request_kick_mode(self, mode: KickMode) -> None:
        self._kick_mode = mode

    def request_visualization_mode(self, mode: MusicVisualizationMode) -> None:
        self._visualization_mode = mode
        if self._ui:
            self._ui.set_visualization_mode(mode)
