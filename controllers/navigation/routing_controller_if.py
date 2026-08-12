# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Public interface for route-planning controllers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .routing_types import RouteRequest, RouteResult


class RoutingControllerIf(ABC):
    """Calculate routes between geographic locations."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return whether route calculation is available.

        @retval True Route calculation is available.
        @retval False Route calculation is unavailable.
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
        """Calculate and return a route.

        @param request Origin, destination, and travel mode.
        @return Calculated route.
        """
        ...
