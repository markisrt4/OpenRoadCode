"""! @brief Callback contract for radio station-navigation requests."""

from abc import ABC, abstractmethod


class StationRequestHandlerIf(ABC):
    """! @brief Handle station-navigation requests produced by a radio UI."""

    @abstractmethod
    def request_next_station(self) -> None:
        """! @brief Request the next configured station."""
        ...

    @abstractmethod
    def request_previous_station(self) -> None:
        """! @brief Request the previous configured station."""
        ...
