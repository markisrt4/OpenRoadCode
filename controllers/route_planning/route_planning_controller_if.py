"""Public interface for route-planning controllers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .route_planning_types import (
    RouteRequest,
    RouteResult,
)


class RoutePlanningControllerIf(ABC):
    """Calculate routes between geographic locations."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return whether route planning is currently available.

        @retval True Route planning is available.
        @retval False Route planning is unavailable.
        """
        ...

    @property
    @abstractmethod
    def status_message(self) -> str | None:
        """Return an availability or error message, if applicable.

        @return Human-readable status, or ``None`` when no message applies.
        """
        ...

    @abstractmethod
    def calculate_route(
        self,
        request: RouteRequest,
    ) -> RouteResult:
        """Calculate a route.

        @param request Origin, destination, and travel mode.
        @return Calculated route.
        """
        ...

