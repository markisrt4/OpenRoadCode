# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic requests emitted by a route-guidance UI."""

from abc import ABC, abstractmethod

from ui.navigation.map_ui_if import GeoPoint
from ui.navigation.route_types import TravelMode


class RouteRequestHandlerIf(ABC):
    """Start and cancel single-destination guidance.

    Advanced operations require their separate capability ABCs. Frontends use
    isinstance(handler, CapabilityIf) before exposing the corresponding controls.
    """

    @property
    @abstractmethod
    def supported_travel_modes(self) -> frozenset[TravelMode]:
        """Expose the costing modes this handler can start routes with.

        @return Immutable set of supported route costing modes.
        """
        ...

    @abstractmethod
    def request_start_route(
        self,
        destination: GeoPoint,
        travel_mode: TravelMode,
    ) -> None:
        """Request route calculation and guidance.

        @param destination Requested final destination.
        @param travel_mode Requested route costing mode.

        Unsupported travel modes raise ValueError before starting a route.
        """
        ...

    @abstractmethod
    def request_cancel_route(self) -> None:
        """Request cancellation of active route guidance."""
        ...
