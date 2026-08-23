# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod

from controllers.music_lighting.music_lighting_types import MusicLightingPatternId


class MusicLightingRequestHandlerIf(ABC):
    """Handle semantic requests for music-reactive lighting."""

    @abstractmethod
    def request_enabled(self, enabled: bool) -> None:
        """Enable or disable music-reactive output.

        @param enabled Requested enabled state.
        """
        ...

    @abstractmethod
    def request_pattern(self, pattern: MusicLightingPatternId) -> None:
        """Select a music-lighting pattern.

        @param pattern Selected pattern identifier.
        """
        ...

    @abstractmethod
    def request_intensity(self, intensity: float) -> None:
        """Set effect intensity.

        @param intensity Normalized intensity from zero through one.
        """
        ...

    @abstractmethod
    def request_brightness_limit(self, percent: int) -> None:
        """Set the maximum output brightness.

        @param percent Brightness limit from zero through 100.
        """
        ...
