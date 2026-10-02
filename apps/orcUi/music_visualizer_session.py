# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Session adapter between shared music analysis and the ORC visualizer panel."""

from __future__ import annotations

from collections.abc import Callable

from apps.orcUi.frontend.tk.music_visualizer_panel import VisualizerFrame
from controllers.audio.capture import AudioCaptureIf
from controllers.audio.music_analysis.music_analysis_session import MusicAnalysisSession
from controllers.audio.music_analysis.music_analysis_types import MusicAnalysisState

VisualizerFrameCallback = Callable[[VisualizerFrame], None]


class MusicVisualizerSession:
    """Own a music-analysis pipeline and adapt its state for the ORC frontend."""

    def __init__(
        self,
        capture_factory: Callable[[], AudioCaptureIf],
        callback: VisualizerFrameCallback,
    ) -> None:
        self._callback = callback
        self._session = MusicAnalysisSession(
            {"capture": capture_factory}, consumer=self._on_analysis_state,
        )

    @property
    def is_running(self) -> bool:
        return bool(self._session.state()["running"])

    @property
    def is_zeroized(self) -> bool:
        return bool(self._session.state()["zeroized"])

    def start(self) -> None:
        self._session.start("capture")

    def stop(self) -> None:
        self._session.stop()

    def close(self) -> None:
        self.stop()

    def start_zeroize(self) -> None:
        self._session.start_zeroize()

    def finish_zeroize(self) -> None:
        self._session.finish_zeroize()

    def clear_zeroize(self) -> None:
        self._session.clear_zeroize()

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
