# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-neutral UI contract for analyzed music data."""
from __future__ import annotations

from abc import ABC, abstractmethod

from controllers.audio_analysis.music_analysis import MusicAnalysisState
from .music_analysis_types import MusicAnalysisUiState


class MusicAnalysisUiIf(ABC):
    """State pushed from music-analysis logic into a frontend."""

    @abstractmethod
    def set_analysis_state(self, state: MusicAnalysisState) -> None:
        """Display one live music-analysis frame.

        @param state Normalized audio, spectrum, and percussion state.
        """
        ...

    @abstractmethod
    def set_analysis_ui_state(self, state: MusicAnalysisUiState) -> None:
        """Display analysis lifecycle and configuration state.

        @param state Current analysis UI state.
        """
        ...
