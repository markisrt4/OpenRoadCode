# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Source boundary for frontend-neutral music analysis."""
from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from .audio_analysis import SpectrumAnalysisMode
from .music_analysis import MusicAnalysisState
from .selectable_music_analysis_source import MusicAudioInput


class MusicAnalysisSourceIf(Protocol):
    """Produce normalized music-analysis state independent of audio backend."""

    @property
    def sensitivity(self) -> float:
        """Return the current normalized analysis sensitivity.

        @return Sensitivity multiplier.
        """
        ...

    @property
    def calibrated(self) -> bool:
        """Return whether ambient-noise calibration is active.

        @return True when calibrated.
        """
        ...

    @property
    def spectrum_mode(self) -> SpectrumAnalysisMode:
        """Return the selected spectrum analysis mode.

        @return Current spectrum mode.
        """
        ...

    @property
    def buffered_audio_seconds(self) -> float:
        """Return the duration of fresh PCM retained for recognition.

        @return Buffered duration in seconds.
        """
        ...

    def start(self, callback: Callable[[MusicAnalysisState], None]) -> None:
        """Start analysis delivery.

        @param callback Consumer for analysis states.
        """
        ...

    def stop(self) -> None:
        """Stop analysis and release capture resources."""
        ...

    @property
    def input(self) -> MusicAudioInput:
        """Return the currently selected capture input."""
        ...

    def select_input(self, selected: MusicAudioInput | str) -> None:
        """Switch to another configured capture input."""
        ...

    def zeroize(self) -> None:
        """Begin ambient-noise calibration."""
        ...

    def set_sensitivity(self, value: float) -> None:
        """Set normalized analysis sensitivity.

        @param value Sensitivity multiplier.
        """
        ...

    def set_spectrum_mode(self, mode: SpectrumAnalysisMode | str) -> None:
        """Select the spectrum calculation mode.

        @param mode Spectrum mode or its serialized value.
        """
        ...

    def recent_audio_pcm16(self, seconds: float = 6.0) -> bytes:
        """Return recent fresh audio as signed 16-bit PCM.

        @param seconds Maximum requested duration.
        @return Little-endian mono PCM bytes.
        """
        ...

    def recent_audio_wav(self, seconds: float = 6.0) -> bytes:
        """Return recent fresh audio in a WAV container.

        @param seconds Maximum requested duration.
        @return Mono 16-bit PCM WAV bytes.
        """
        ...
