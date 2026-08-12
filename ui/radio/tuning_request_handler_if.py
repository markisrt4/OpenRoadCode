# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""! @brief Callback contract for radio tuning requests."""

from abc import ABC, abstractmethod


class TuningRequestHandlerIf(ABC):
    """! @brief Handle frequency-step requests produced by a radio UI."""

    @abstractmethod
    def request_tune_up(self) -> None:
        """! @brief Request one upward frequency step."""
        ...

    @abstractmethod
    def request_tune_down(self) -> None:
        """! @brief Request one downward frequency step."""
        ...
