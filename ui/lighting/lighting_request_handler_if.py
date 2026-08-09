"""Requests emitted by a lighting control UI."""

from abc import ABC, abstractmethod

from ui.lighting.lighting_ui_if import LightingColor


class LightingRequestHandlerIf(ABC):
    """Handle semantic lighting changes requested by a UI."""

    @abstractmethod
    def request_power(self, enabled: bool) -> None:
        """Request that lighting power be enabled or disabled.

        @param enabled True to enable lighting power.
        """
        ...

    @abstractmethod
    def request_color(self, color: LightingColor) -> None:
        """Request a normalized RGB lighting color.

        @param color Requested RGB color.
        """
        ...

    @abstractmethod
    def request_brightness(self, percent: int) -> None:
        """Request brightness from zero through 100 percent.

        @param percent Requested brightness percentage in the range 0..100.
        """
        ...

    @abstractmethod
    def request_pattern(self, pattern_index: int) -> None:
        """Request a controller lighting pattern.

        @param pattern_index Controller-defined pattern index.
        """
        ...

    @abstractmethod
    def request_music_mode(self, mode_index: int) -> None:
        """Request a music-reactive mode.

        @param mode_index Controller-defined music mode index.
        """
        ...
