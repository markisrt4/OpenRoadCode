# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Source boundary for frontend-neutral music analysis."""
from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from .audio_analysis import SpectrumAnalysisMode
from .music_analysis import MusicAnalysisState


class MusicAnalysisSourceIf(Protocol):
    """Produce normalized music-analysis state independent of audio backend."""

    @property
    def sensitivity(self) -> float: ...

    @property
    def calibrated(self) -> bool: ...

    @property
    def spectrum_mode(self) -> SpectrumAnalysisMode: ...

    def start(self, callback: Callable[[MusicAnalysisState], None]) -> None: ...

    def stop(self) -> None: ...

    def zeroize(self) -> None: ...

    def set_sensitivity(self, value: float) -> None: ...

    def set_spectrum_mode(self, mode: SpectrumAnalysisMode | str) -> None: ...

    def recent_audio_pcm16(self, seconds: float = 6.0) -> bytes: ...
