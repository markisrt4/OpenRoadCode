# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic requests from radar replay controls."""

from abc import ABC, abstractmethod
from ui.weather.radar_ui_if import RadarPalette


class RadarRequestHandlerIf(ABC):
    @abstractmethod
    def request_enabled(self, enabled: bool) -> None:
        """Set radar visibility.

        @param enabled Whether radar should be displayed.
        """
        ...

    @abstractmethod
    def request_previous(self) -> None:
        """Select the previous radar frame."""
        ...

    @abstractmethod
    def request_next(self) -> None:
        """Select the next radar frame."""
        ...

    @abstractmethod
    def request_live(self) -> None:
        """Return from forecast/history to current observed radar."""
        ...

    @abstractmethod
    def request_source(self, forecast: bool) -> None:
        """Select observed or forecast radar.

        @param forecast Whether to select forecast data.
        """
        ...

    @abstractmethod
    def request_seek(self, index: int) -> None:
        """Pause playback and select a cached frame.

        @param index Zero-based frame index.
        """
        ...

    @abstractmethod
    def request_play_pause(self) -> None:
        """Toggle replay playback."""
        ...

    @abstractmethod
    def request_speed(self, speed: float) -> None:
        """Choose a replay speed.

        @param speed Positive playback multiplier.
        """
        ...

    @abstractmethod
    def request_palette(self, palette: RadarPalette) -> None:
        """Choose a color presentation.

        @param palette Universal or classic colors.
        """
        ...

    @abstractmethod
    def request_navigation_visible(self, visible: bool) -> None:
        """Pause replay when leaving Navigation.

        @param visible Whether Navigation is shown.
        """
        ...

    @abstractmethod
    def request_replay(self) -> None:
        """Restore requested radar after renderer replacement."""
        ...
