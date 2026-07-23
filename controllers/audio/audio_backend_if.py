from __future__ import annotations

from abc import ABC, abstractmethod


class AudioBackendIf(ABC):
    """
    Interface for controlling an audio output backend.
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
        """Set the discrete volume level.

        @param level Requested level; implementations clamp it to their range.
        @return Resulting discrete volume level after clamping.
        """
