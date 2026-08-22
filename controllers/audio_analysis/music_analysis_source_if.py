# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Source boundary for frontend-neutral music analysis."""
from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from .music_analysis import MusicAnalysisState


class MusicAnalysisSourceIf(Protocol):
    """Produce normalized music-analysis state independent of audio backend."""

    @property
    def sensitivity(self) -> float: ...

    @property
    def calibrated(self) -> bool: ...

    def start(self, callback: Callable[[MusicAnalysisState], None]) -> None: ...

    def stop(self) -> None: ...

    def zeroize(self) -> None: ...

    def set_sensitivity(self, value: float) -> None: ...

    def recent_audio_pcm16(self, seconds: float = 6.0) -> bytes: ...
