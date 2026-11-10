# SPDX-License-Identifier: MIT

"""Optional route capability; advertise only when implemented."""

from abc import ABC, abstractmethod


class RouteRecalculationRequestHandlerIf(ABC):
    """Explicitly recalculate guidance from current position."""

    @abstractmethod
    def request_recalculate_route(self) -> None:
        """Request immediate route recalculation from current position."""
        ...
