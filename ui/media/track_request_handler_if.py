"""! @brief Callback contract for media track-navigation requests."""

from abc import ABC, abstractmethod


class TrackRequestHandlerIf(ABC):
    """! @brief Handle previous and next track requests from a media UI."""

    @abstractmethod
    def request_previous_track(self) -> None:
        """! @brief Request the previous track."""
        ...

    @abstractmethod
    def request_next_track(self) -> None:
        """! @brief Request the next track."""
        ...
