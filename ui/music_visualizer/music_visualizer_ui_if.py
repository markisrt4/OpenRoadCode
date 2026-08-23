# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-neutral UI contract for music visualization."""
from __future__ import annotations

from abc import ABC, abstractmethod

from controllers.song_recognition.song_recognition_if import SongRecognitionResult
from .music_visualizer_types import MusicVisualizationMode, SongRecognitionUiState


class MusicVisualizerUiIf(ABC):
    """Visualizer-specific state pushed into a frontend."""

    @abstractmethod
    def set_song(self, song: SongRecognitionResult | None) -> None:
        """Display recognized song metadata.

        @param song Recognized song or None when unavailable.
        """
        ...

    @abstractmethod
    def set_song_recognition_state(self, state: SongRecognitionUiState) -> None:
        """Display recognition readiness and request status.

        @param state Current recognition UI state.
        """
        ...

    @abstractmethod
    def set_visualization_mode(self, mode: MusicVisualizationMode) -> None:
        """Display the selected visualization mode.

        @param mode Active visualization mode.
        """
        ...
