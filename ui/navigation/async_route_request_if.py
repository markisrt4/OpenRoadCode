# SPDX-License-Identifier: MIT
"""Optional nonblocking route-start capability."""

from abc import ABC, abstractmethod

from ui.navigation.map_ui_if import GeoPoint
from ui.navigation.route_types import TravelMode


class AsyncRouteRequestIf(ABC):
    """Submit guidance requests and observe their completion."""

    @property
    @abstractmethod
    def route_start_pending(self) -> bool:
        """Return whether a route start is in progress.

        @return True while a route start is pending.
        """
        ...

    @abstractmethod
    def request_start_route_async(self, destination: GeoPoint, travel_mode: TravelMode) -> None:
        """Submit a route start without blocking the caller.

        @param destination Destination coordinates in radians.
        @param travel_mode Requested routing mode.
        """
        ...
