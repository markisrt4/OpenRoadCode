"""! @brief Callback contract for system volume requests."""

from abc import ABC, abstractmethod


class VolumeRequestHandlerIf(ABC):
    """! @brief Handle system volume requests produced by a UI."""

    @abstractmethod
    def request_volume(self, volume_percent: float) -> None:
        """! @brief Request an absolute system volume.

        @param volume_percent Requested volume from 0 through 100.
        """
        ...

    @abstractmethod
    def request_volume_up(self) -> None:
        """! @brief Request one implementation-defined volume increase."""
        ...

    @abstractmethod
    def request_volume_down(self) -> None:
        """! @brief Request one implementation-defined volume decrease."""
        ...

    @abstractmethod
    def request_mute(self, muted: bool) -> None:
        """! @brief Request an explicit system mute state.

        @param muted True to mute system audio; false to make it audible.
        """
        ...
