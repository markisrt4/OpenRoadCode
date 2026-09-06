# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Session adapter between shared music analysis and the ORC visualizer panel."""

from __future__ import annotations

from collections.abc import Callable

from apps.orcUi.music_visualizer_panel import VisualizerFrame
from controllers.audio.music_analysis.music_analysis_pipeline import MusicAnalysisPipeline
from controllers.audio.music_analysis.music_analysis_types import MusicAnalysisState

VisualizerFrameCallback = Callable[[VisualizerFrame], None]


class MusicVisualizerSession:
    """Own a music-analysis pipeline and adapt its state for the ORC frontend."""

    def __init__(
        self,
        pipeline_factory: Callable[[Callable[[MusicAnalysisState], None]], MusicAnalysisPipeline],
        callback: VisualizerFrameCallback,
    ) -> None:
        self._callback = callback
        self._pipeline = pipeline_factory(self._on_analysis_state)

    @property
    def is_running(self) -> bool:
        return self._pipeline.is_running

    @property
    def is_zeroized(self) -> bool:
        return self._pipeline.is_zeroized

    def start(self) -> None:
        if not self._pipeline.is_running:
            self._pipeline.start()

    def stop(self) -> None:
        if self._pipeline.is_running:
            self._pipeline.stop()

    def close(self) -> None:
        self.stop()

    def start_zeroize(self) -> None:
        self._pipeline.start_zeroize()

    def finish_zeroize(self) -> None:
        self._pipeline.finish_zeroize()

    def clear_zeroize(self) -> None:
        self._pipeline.clear_zeroize()

    def _on_analysis_state(self, state: MusicAnalysisState) -> None:
        self._callback(self.to_visualizer_frame(state))

    @staticmethod
    def to_visualizer_frame(state: MusicAnalysisState) -> VisualizerFrame:
        """Translate frontend-neutral analyzer state to the Tk panel snapshot."""
        return VisualizerFrame(
            level=state.level,
            bass=state.bass,
            mid=state.mid,
            treble=state.treble,
            spectrum=state.spectrum,
        )
