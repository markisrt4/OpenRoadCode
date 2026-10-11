# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Audio-independent presentation boundary for native visualizer renderers."""
from abc import ABC, abstractmethod
from ui.ui_widget import UiWidget
from .music_visualizer_types import VisualizerFrame


class MusicVisualizerPresentationIf(UiWidget, ABC):
    """Consume immutable analysis snapshots and release animation resources."""

    @abstractmethod
    def set_analysis_frame(self, frame: VisualizerFrame) -> None:
        """Present analysis without acquiring or changing the audio source."""

    @abstractmethod
    def close(self) -> None:
        """Stop animation and release renderer resources; safe to call repeatedly."""
