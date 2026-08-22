# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-neutral coordination for visualizer-specific behavior."""
from __future__ import annotations

from collections.abc import Callable

from controllers.song_recognition import SongRecognitionController, SongRecognitionResult
from ui.music_visualizer import (
    KickMode,
    MusicVisualizationMode,
    MusicVisualizerRequestHandlerIf,
    MusicVisualizerUiIf,
    SongRecognitionUiState,
)


class MusicVisualizerPresenter(MusicVisualizerRequestHandlerIf):
    """Coordinate visualization selection and song recognition."""

    def __init__(
        self,
        song_recognition: SongRecognitionController,
        *,
        dispatch: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        self._song_recognition = song_recognition
        self._dispatch = dispatch or (lambda callback: callback())
        self._ui: MusicVisualizerUiIf | None = None
        self._kick_mode = KickMode.SINGLE
        self._visualization_mode = MusicVisualizationMode.SPECTRUM

    def attach_ui(self, ui: MusicVisualizerUiIf) -> None:
        self._ui = ui
        ui.set_visualization_mode(self._visualization_mode)
        ui.set_song_recognition_state(
            SongRecognitionUiState(
                configured=self._song_recognition.is_configured,
                provider=self._song_recognition.provider_name,
            )
        )

    def detach_ui(self) -> None:
        self._ui = None

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
                SongRecognitionUiState(
                    configured=True,
                    recognizing=False,
                    provider=self._song_recognition.provider_name,
                )
            )

    def _recognition_result(self, result: SongRecognitionResult | None) -> None:
        self._dispatch(lambda: self._present_recognition_result(result))

    def _present_recognition_result(self, result: SongRecognitionResult | None) -> None:
        if self._ui:
            self._ui.set_song(result)
            self._ui.set_song_recognition_state(
                SongRecognitionUiState(
                    configured=self._song_recognition.is_configured,
                    provider=self._song_recognition.provider_name,
                )
            )

    def _recognition_error(self, message: str) -> None:
        self._dispatch(lambda: self._present_recognition_error(message))

    def _present_recognition_error(self, message: str) -> None:
        if self._ui:
            # Recognition remains a visualizer concern, but the frontend decides
            # how an unavailable result is represented rather than receiving prose.
            self._ui.set_song(None)
            self._ui.set_song_recognition_state(
                SongRecognitionUiState(
                    configured=self._song_recognition.is_configured,
                    recognizing=False,
                    provider=self._song_recognition.provider_name,
                )
            )

    def request_kick_mode(self, mode: KickMode) -> None:
        self._kick_mode = mode

    def request_visualization_mode(self, mode: MusicVisualizationMode) -> None:
        self._visualization_mode = mode
        if self._ui:
            self._ui.set_visualization_mode(mode)
