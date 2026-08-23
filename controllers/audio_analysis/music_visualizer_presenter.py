# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-neutral coordination for visualizer-specific behavior."""
from __future__ import annotations

from collections.abc import Callable
import logging

from controllers.song_recognition import SongRecognitionController, SongRecognitionResult
from ui.music_visualizer import (
    KickMode,
    MusicVisualizationMode,
    MusicVisualizerRequestHandlerIf,
    MusicVisualizerUiIf,
    SongRecognitionUiState,
)

LOGGER=logging.getLogger(__name__)


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
        self._last_buffer_second = -1

    def attach_ui(self, ui: MusicVisualizerUiIf) -> None:
        self._ui = ui
        ui.set_visualization_mode(self._visualization_mode)
        self._publish_recognition_readiness()

    def detach_ui(self) -> None:
        self._ui = None

    def request_song_recognition(self) -> None:
        if not self._song_recognition.is_configured:
            LOGGER.warning("Song recognition requested but no provider is configured")
            if self._ui:
                self._ui.set_song_recognition_state(SongRecognitionUiState(configured=False))
            return
        if not self._song_recognition.is_ready:
            self._publish_recognition_readiness()
            return
        if self._ui:
            self._ui.set_song_recognition_state(
                SongRecognitionUiState(
                    configured=True,
                    recognizing=True,
                    ready=True,
                    buffered_seconds=self._song_recognition.buffered_audio_seconds,
                    provider=self._song_recognition.provider_name,
                )
            )
        started = self._song_recognition.identify_async(self._recognition_result, self._recognition_error)
        if not started and self._ui:
            self._ui.set_song_recognition_state(
                SongRecognitionUiState(
                    configured=True,
                    recognizing=False,
                    ready=self._song_recognition.is_ready,
                    buffered_seconds=self._song_recognition.buffered_audio_seconds,
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
                    ready=self._song_recognition.is_ready,
                    buffered_seconds=self._song_recognition.buffered_audio_seconds,
                    provider=self._song_recognition.provider_name,
                    message=("No song match found · "+(self._song_recognition.last_clip_summary or "clip submitted")) if result is None else None,
                )
            )

    def _recognition_error(self, message: str) -> None:
        self._dispatch(lambda: self._present_recognition_error(message))

    def _present_recognition_error(self, message: str) -> None:
        LOGGER.error("Song recognition failed: %s",message)
        if self._ui:
            self._ui.set_song(None)
            self._ui.set_song_recognition_state(
                SongRecognitionUiState(
                    configured=self._song_recognition.is_configured,
                    recognizing=False,
                    ready=self._song_recognition.is_ready,
                    buffered_seconds=self._song_recognition.buffered_audio_seconds,
                    provider=self._song_recognition.provider_name,
                    message=f"Recognition failed: {message}",
                )
            )

    def audio_buffer_updated(self, _state: object | None = None) -> None:
        """Publish readiness when another whole second of audio is buffered."""
        second = min(10, int(self._song_recognition.buffered_audio_seconds))
        if second == self._last_buffer_second:
            return
        self._last_buffer_second = second
        self._dispatch(self._publish_recognition_readiness)

    def _publish_recognition_readiness(self) -> None:
        if self._ui is None:
            return
        buffered = self._song_recognition.buffered_audio_seconds
        ready = self._song_recognition.is_ready
        self._ui.set_song_recognition_state(
            SongRecognitionUiState(
                configured=self._song_recognition.is_configured,
                ready=ready,
                buffered_seconds=buffered,
                provider=self._song_recognition.provider_name,
                message=None if ready else f"Buffering audio… {min(10, int(buffered))}/10s",
            )
        )

    def request_kick_mode(self, mode: KickMode) -> None:
        self._kick_mode = mode

    def request_visualization_mode(self, mode: MusicVisualizationMode) -> None:
        self._visualization_mode = mode
        if self._ui:
            self._ui.set_visualization_mode(mode)
