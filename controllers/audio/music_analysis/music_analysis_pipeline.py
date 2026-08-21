# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Composition layer joining PCM capture to music analysis."""
from __future__ import annotations

from collections.abc import Callable

from controllers.audio.capture.audio_capture_if import AudioCaptureIf

from .music_analysis_types import MusicAnalysisState
from .music_analyzer_if import MusicAnalyzerIf

MusicAnalysisCallback = Callable[[MusicAnalysisState], None]


class MusicAnalysisPipeline:
    """Feed captured PCM into an analyzer and publish analysis states."""

    def __init__(
        self,
        capture: AudioCaptureIf,
        analyzer: MusicAnalyzerIf,
        callback: MusicAnalysisCallback,
    ) -> None:
        self._capture = capture
        self._analyzer = analyzer
        self._callback = callback

    @property
    def is_running(self) -> bool:
        return self._capture.is_running

    @property
    def is_zeroized(self) -> bool:
        return self._analyzer.is_zeroized

    def start(self) -> None:
        self._capture.start(self._on_samples)

    def stop(self) -> None:
        self._capture.stop()

    def start_zeroize(self) -> None:
        self._analyzer.start_zeroize()

    def finish_zeroize(self) -> None:
        self._analyzer.finish_zeroize()

    def clear_zeroize(self) -> None:
        self._analyzer.clear_zeroize()

    def _on_samples(self, samples, sample_rate_hz: int) -> None:
        state = self._analyzer.analyze(samples, sample_rate_hz)
        self._callback(state)
