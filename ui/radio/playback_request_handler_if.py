"""! @brief Callback contract for radio playback requests."""

from abc import ABC, abstractmethod


class PlaybackRequestHandlerIf(ABC):
    """! @brief Handle play and pause requests produced by a radio UI."""

    @abstractmethod
    def request_play(self) -> None:
        """! @brief Request radio playback."""
        ...

    @abstractmethod
    def request_pause(self) -> None:
        """! @brief Request radio playback to pause."""
        ...
