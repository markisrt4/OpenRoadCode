# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""! @brief Callback contract for vehicle diagnostic requests."""

from abc import ABC, abstractmethod


class DiagnosticsRequestHandlerIf(ABC):
    """! @brief Handle diagnostic actions requested by a vehicle UI."""

    @abstractmethod
    def request_clear_diagnostics(self) -> None:
        """! @brief Request that vehicle diagnostic trouble codes be cleared."""
        ...
