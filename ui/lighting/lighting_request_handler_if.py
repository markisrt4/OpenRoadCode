# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Requests emitted by a lighting control UI."""

from abc import abstractmethod

from ui.value import BrightnessValueRequestHandlerIf, ColorValueRequestHandlerIf


class LightingRequestHandlerIf(
    ColorValueRequestHandlerIf,
    BrightnessValueRequestHandlerIf,
):
    """Handle lighting-specific requests plus generic color/brightness intent."""

    @abstractmethod
    def request_power(self, enabled: bool) -> None:
        """Request that lighting power be enabled or disabled.

        @param enabled True to enable lighting power.
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
