"""! @brief Callback contract for media volume requests."""

from abc import ABC, abstractmethod


class VolumeRequestHandlerIf(ABC):
    """! @brief Handle volume requests produced by a media UI."""

    @abstractmethod
    def request_volume(self, volume_percent: int) -> None:
        """! @brief Request a media playback volume.

        @param volume_percent Requested volume from 0 through 100.
        """
        ...
