# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""! @brief Callback contract for media seek requests."""

from abc import ABC, abstractmethod


class SeekRequestHandlerIf(ABC):
    """! @brief Handle relative and absolute seek requests from a media UI."""

    @abstractmethod
    def request_rewind(self, seconds: float) -> None:
        """! @brief Request a backward seek from the current position.

        @param seconds Non-negative number of seconds to rewind.
        """
        ...

    @abstractmethod
    def request_forward(self, seconds: float) -> None:
        """! @brief Request a forward seek from the current position.

        @param seconds Non-negative number of seconds to advance.
        """
        ...

    @abstractmethod
    def request_seek(self, position_s: float) -> None:
        """! @brief Request an absolute position in the current media item.

        @param position_s Zero-based playback position in seconds.
        """
        ...
