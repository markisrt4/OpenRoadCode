# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Audio-independent presentation boundary for native visualizer renderers."""
from abc import ABC, abstractmethod
from ui.ui_widget import UiWidget
from .music_visualizer_types import MusicVisualizerOptions, VisualizerFrame


class MusicVisualizerPresentationIf(UiWidget, ABC):
    """Consume immutable analysis snapshots and release animation resources."""

    @abstractmethod
    def set_analysis_frame(self, frame: VisualizerFrame) -> None:
        """Present analysis without acquiring or changing the audio source.

        @param frame Immutable snapshot from the audio-analysis controller.
        """

    @abstractmethod
    def close(self) -> None:
        """Stop animation and release renderer resources; safe to call repeatedly."""

    @abstractmethod
    def configure_visualizer(self, options: MusicVisualizerOptions) -> None:
        """Apply rendering settings without restarting the audio session.

        @param options Semantic presentation settings selected by the user.
        """

    @abstractmethod
    def presentation_status(self) -> str:
        """Report the renderer state without exposing backend internals.

        @return Human-readable renderer status or graphics initialization error.
        """
