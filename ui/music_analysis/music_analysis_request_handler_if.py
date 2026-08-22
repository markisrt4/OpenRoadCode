# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic requests emitted by music-analysis frontends."""
from __future__ import annotations

from abc import ABC, abstractmethod

from controllers.audio_analysis.audio_analysis import SpectrumAnalysisMode


class MusicAnalysisRequestHandlerIf(ABC):
    @abstractmethod
    def request_zeroize(self) -> None: ...

    @abstractmethod
    def request_sensitivity(self, value: float) -> None: ...

    @abstractmethod
    def request_spectrum_mode(self, mode: SpectrumAnalysisMode) -> None: ...
