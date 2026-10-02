# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Frontend-neutral audio lifecycle and presentation boundary."""
from abc import ABC, abstractmethod
from .music_visualizer_types import MusicVisualizerSource, VisualizerFrame


class MusicVisualizerControlIf(ABC):
    """Nonblocking controls consumed by visualizer frontends."""

    @abstractmethod
    def start(self, source: MusicVisualizerSource) -> None:
        """Select and asynchronously start an input.

        @param source Semantic input choice.
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        """Invalidate pending work and asynchronously release capture."""
        ...

    @abstractmethod
    def calibrate(self, action: str) -> None:
        """Request ambient-noise calibration.

        @param action Calibration operation name.
        """
        ...

    @abstractmethod
    def presentation(self) -> tuple[VisualizerFrame | None, str | None]:
        """Consume the latest frame and status without waiting.

        @return Latest available frame and status, or None for unchanged fields.
        """
        ...
