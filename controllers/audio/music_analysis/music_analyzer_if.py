# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-neutral music analyzer interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .music_analysis_types import MusicAnalysisState


class MusicAnalyzerIf(ABC):
    """Analyze PCM samples into a frontend-neutral music state."""

    @abstractmethod
    def analyze(
        self,
        samples: Sequence[float],
        sample_rate_hz: int,
    ) -> MusicAnalysisState:
        """Analyze one block of normalized mono PCM samples."""
        raise NotImplementedError

    @abstractmethod
    def start_zeroize(self) -> None:
        """Begin collecting ambient-noise calibration blocks."""
        raise NotImplementedError

    @abstractmethod
    def finish_zeroize(self) -> None:
        """Commit the collected ambient-noise calibration."""
        raise NotImplementedError

    @abstractmethod
    def clear_zeroize(self) -> None:
        """Discard the current ambient-noise calibration."""
        raise NotImplementedError

    @property
    @abstractmethod
    def is_zeroized(self) -> bool:
        """Return whether an ambient-noise calibration is active."""
        raise NotImplementedError
