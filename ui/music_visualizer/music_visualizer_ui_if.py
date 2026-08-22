# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-neutral UI contract for music visualization."""
from __future__ import annotations

from abc import ABC, abstractmethod

from controllers.audio_analysis.music_analysis import MusicAnalysisState
from controllers.song_recognition.song_recognition_if import SongRecognitionResult
from .music_visualizer_types import MusicVisualizationMode, SongRecognitionUiState


class MusicVisualizerUiIf(ABC):
    """State pushed from music-visualizer logic into a frontend."""

    @abstractmethod
    def set_analysis_state(self, state: MusicAnalysisState) -> None: ...

    @abstractmethod
    def set_song(self, song: SongRecognitionResult | None) -> None: ...

    @abstractmethod
    def set_song_recognition_state(self, state: SongRecognitionUiState) -> None: ...

    @abstractmethod
    def set_zeroize_state(self, calibrated: bool, calibrating: bool) -> None: ...

    @abstractmethod
    def set_sensitivity(self, sensitivity: float) -> None: ...

    @abstractmethod
    def set_lighting_enabled(self, enabled: bool) -> None: ...

    @abstractmethod
    def set_visualization_mode(self, mode: MusicVisualizationMode) -> None: ...

    @abstractmethod
    def set_status(self, message: str) -> None: ...
