# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent contracts for displaying and requesting a color value."""

from abc import ABC, abstractmethod

from common.color import RgbColor


class ColorValueUiIf(ABC):
    """Accept a normalized RGB color for presentation by a UI."""

    @abstractmethod
    def set_color(self, color: RgbColor) -> None:
        """Set the color displayed by the UI.

        @param color Normalized RGB color to display.
        """
        ...


class ColorValueRequestHandlerIf(ABC):
    """Handle a semantic color selection emitted by a UI."""

    @abstractmethod
    def request_color(self, color: RgbColor) -> None:
        """Request a normalized RGB color.

        @param color Requested RGB color.
        """
        ...
