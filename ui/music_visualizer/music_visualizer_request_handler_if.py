# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic user requests emitted by music visualizer frontends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .music_visualizer_types import KickMode, MusicVisualizationMode


class MusicVisualizerRequestHandlerIf(ABC):
    """Handle semantic requests from music-visualizer frontends."""

    @abstractmethod
    def request_kick_mode(self, mode: KickMode) -> None:
        """Select the rendered kick-drum layout.

        @param mode Kick-drum layout to activate.
        """
        ...

    @abstractmethod
    def request_visualization_mode(self, mode: MusicVisualizationMode) -> None:
        """Select the active visualization renderer.

        @param mode Visualization mode to activate.
        """
        ...
