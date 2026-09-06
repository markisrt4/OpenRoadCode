# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Development-only contract for driving simulated navigation along a route."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from controllers.route_planning.route_planning_types import RouteResult


@runtime_checkable
class RouteSimulationIf(Protocol):
    """Allow a navigation input source to follow an already-calculated route."""

    def follow_route(self, route: RouteResult, *, time_scale: float = 60.0) -> None:
        """Begin following ``route`` at an accelerated simulation rate."""
        ...

    def stop_route(self) -> None:
        """Stop route following and return to the source's normal simulation."""
        ...
