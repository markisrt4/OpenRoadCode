# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent contracts for displaying and requesting brightness."""

from abc import ABC, abstractmethod


class BrightnessValueUiIf(ABC):
    """Accept a normalized brightness percentage for presentation by a UI."""

    @abstractmethod
    def set_brightness(self, percent: int) -> None:
        """Set the brightness displayed by the UI.

        @param percent Brightness percentage in the range 0..100.
        """
        ...


class BrightnessValueRequestHandlerIf(ABC):
    """Handle a semantic brightness change emitted by a UI."""

    @abstractmethod
    def request_brightness(self, percent: int) -> None:
        """Request brightness from zero through 100 percent.

        @param percent Requested brightness percentage in the range 0..100.
        """
        ...
