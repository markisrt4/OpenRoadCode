# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic requests emitted by music-analysis frontends."""
from __future__ import annotations

from abc import ABC, abstractmethod

from controllers.audio_analysis.audio_analysis import SpectrumAnalysisMode
from controllers.audio_analysis.selectable_music_analysis_source import MusicAudioInput


class MusicAnalysisRequestHandlerIf(ABC):
    """Handle semantic requests from a music-analysis frontend."""

    @abstractmethod
    def start(self) -> None:
        """Start audio capture and music analysis."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop audio capture and music analysis."""
        ...

    @abstractmethod
    def request_zeroize(self) -> None:
        """Request ambient-noise calibration."""
        ...

    @abstractmethod
    def request_sensitivity(self, value: float) -> None:
        """Request a sensitivity change.

        @param value Normalized sensitivity multiplier.
        """
        ...

    @abstractmethod
    def request_spectrum_mode(self, mode: SpectrumAnalysisMode) -> None:
        """Request a spectrum-analysis mode.

        @param mode Selected spectrum mode.
        """
        ...

    @abstractmethod
    def request_audio_input(self, selected: MusicAudioInput) -> None:
        """Select the audio stream used for analysis."""
        ...
