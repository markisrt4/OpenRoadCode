# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""! @brief Toolkit-independent system lifecycle request contract."""

from abc import ABC, abstractmethod


class SystemLifecycleRequestHandlerIf(ABC):
    """! @brief Handle semantic lifecycle requests produced by a UI."""

    @abstractmethod
    def request_restart_ui(self) -> None:
        """! @brief Request a clean restart of the OpenRoadCode UI process."""
        ...

    @abstractmethod
    def request_poweroff(self) -> None:
        """! @brief Request an operating-system poweroff after UI cleanup."""
        ...
