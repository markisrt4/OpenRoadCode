"""! @brief Callback contract for media playback requests."""

from abc import ABC, abstractmethod


class PlaybackRequestHandlerIf(ABC):
    """! @brief Handle play and pause requests produced by a media UI."""

    @abstractmethod
    def request_play(self) -> None:
        """! @brief Request media playback."""
        ...

    @abstractmethod
    def request_pause(self) -> None:
        """! @brief Request media playback to pause."""
        ...
