# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic requests for simulated traversal of an active route."""

from abc import ABC, abstractmethod


class RouteSimulationRequestHandlerIf(ABC):
    """Control navigation-service route simulation without UI/service coupling."""

    @abstractmethod
    def request_start_route_simulation(self, *, time_scale: float = 60.0) -> None:
        """Start simulated movement along the active route.

        @param time_scale Simulation speed multiplier relative to real time.
        """
        ...

    @abstractmethod
    def request_stop_route_simulation(self) -> None:
        """Stop simulated route traversal and restore normal position input."""
        ...
