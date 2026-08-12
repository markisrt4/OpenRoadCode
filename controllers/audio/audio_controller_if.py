# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from abc import ABC, abstractmethod


class AudioControllerIf(ABC):
    """
    Interface for controlling audio output volume.
    """

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return whether audio control is configured and available.

        @retval True Audio control is available.
        @retval False Audio control is unavailable.
        """

    @property
    @abstractmethod
    def status_message(self) -> str | None:
        """Return an availability message, if one applies.

        @return Human-readable status, or ``None`` when no message applies.
        """

    @property
    @abstractmethod
    def maximum_level(self) -> int:
        """Return the maximum discrete volume level.

        @return Highest level accepted by `set_volume_level`.
        """

    @abstractmethod
    def volume_up(self) -> int:
        """Increase volume by one step.

        @return Resulting discrete volume level.
        """

    @abstractmethod
    def volume_down(self) -> int:
        """Decrease volume by one step.

        @return Resulting discrete volume level.
        """

    @abstractmethod
    def get_volume_level(self) -> int:
        """Return the current volume level.

        @return Current discrete volume level.
        """

    @abstractmethod
    def set_volume_level(self, level: int) -> int:
        """Set the volume level.

        @param level Requested discrete level; values are clamped to the
            controller's supported range.
        @return Resulting discrete volume level after clamping.
        """

    @abstractmethod
    def is_muted(self) -> bool:
        """Return whether audio output is muted.

        @retval True Audio output is muted.
        @retval False Audio output is audible.
        """

    @abstractmethod
    def toggle_mute(self) -> bool:
        """Toggle the mute state.

        @retval True Audio is muted after the operation.
        @retval False Audio is audible after the operation.
        """

    def adjust_volume(self, steps: int) -> int:
        """Adjust the current volume by discrete steps.

        @param steps Signed number of steps; positive raises volume.
        @return Resulting discrete volume level after clamping.
        """
        current_level = self.get_volume_level()
        return self.set_volume_level(current_level + steps)
