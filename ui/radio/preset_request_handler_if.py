"""! @brief Callback contract for radio preset requests."""

from abc import ABC, abstractmethod


class PresetRequestHandlerIf(ABC):
    """! @brief Handle preset-selection requests produced by a radio UI."""

    @abstractmethod
    def request_preset(self, preset_index: int) -> None:
        """! @brief Request tuning to a configured preset.

        @param preset_index Zero-based preset index.
        """
        ...
