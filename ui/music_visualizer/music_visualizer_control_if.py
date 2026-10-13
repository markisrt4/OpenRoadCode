# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Frontend-neutral audio lifecycle and presentation boundary."""
from abc import ABC, abstractmethod
from .music_visualizer_types import MusicCaptureState, MusicVisualizerOptions, MusicVisualizerSource, VisualizerFrame


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


    @abstractmethod
    def latest_frame(self) -> VisualizerFrame | None:
        """Read shared audio state without consuming another view's pending frame.

        @return Current-generation audio snapshot, or None before capture supplies data.
        """

    @abstractmethod
    def visualizer_options(self) -> MusicVisualizerOptions:
        """Read rendering preferences shared by HOME and the full visualizer.

        @return Immutable current presentation settings.
        """

    @abstractmethod
    def configure_visualizer(self, options: MusicVisualizerOptions) -> None:
        """Change presentation settings without restarting capture.

        @param options Immutable user-selected rendering preferences.
        """

    @abstractmethod
    def attach_view(self, owner: str) -> None:
        """Retain the current capture while a visualizer presentation is mounted.

        @param owner Stable identity of the mounted presentation.
        """

    @abstractmethod
    def detach_view(self, owner: str) -> None:
        """Release a presentation; stop capture after a short navigation handoff.

        @param owner Identity previously supplied to attach_view.
        """

    @abstractmethod
    def home_visualizer_enabled(self) -> bool:
        """Read the remembered HOME Media card selection.

        @return True when HOME should mount its visualizer preview.
        """

    @abstractmethod
    def set_home_visualizer_enabled(self, enabled: bool) -> None:
        """Remember which presentation occupies the existing HOME Media card.

        @param enabled True for the visualizer, False for now-playing.
        """

    @abstractmethod
    def selected_source(self) -> MusicVisualizerSource | None:
        """Read the most recently started input for another mounted presentation.

        @return Last selected source, or None before the first start.
        """

    @abstractmethod
    def capture_state(self) -> MusicCaptureState:
        """Read capture lifecycle without waiting or consuming frames.

        @return Idle, starting, or running for the current generation.
        """
