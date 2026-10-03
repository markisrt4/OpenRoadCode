# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""! @brief Requests emitted by a weather UI."""

from abc import ABC, abstractmethod


class WeatherRequestHandlerIf(ABC):
    """! @brief Handle semantic requests produced by a weather UI."""

    @abstractmethod
    def request_refresh(self) -> None:
        """! @brief Request fresh weather data."""
        ...
