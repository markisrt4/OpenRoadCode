# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""! @brief Explicit UI contract for system volume state."""

from abc import ABC, abstractmethod

from ui.system.volume_request_handler_if import VolumeRequestHandlerIf


class VolumeUiIf(ABC):
    """! @brief Display normalized system volume and mute state.

    This contract does not prescribe discrete steps, visual indicators, audio
    backends, or widget placement. ``None`` means the state is unavailable.
    """

    @abstractmethod
    def set_volume(self, volume_percent: float | None) -> None:
        """! @brief Set the displayed system volume.

        @param volume_percent Volume from 0 through 100, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_muted(self, muted: bool | None) -> None:
        """! @brief Set the displayed system mute state.

        @param muted Mute state, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_volume_request_handler(
        self,
        handler: VolumeRequestHandlerIf | None,
    ) -> None:
        """! @brief Set or clear the system volume request handler.

        @param handler Volume request handler, or None to disconnect it.
        """
        ...
