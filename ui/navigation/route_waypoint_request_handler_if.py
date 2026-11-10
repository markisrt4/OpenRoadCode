# SPDX-License-Identifier: MIT

"""Optional route capability; advertise only when implemented."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from ui.navigation.map_ui_if import GeoPoint
from ui.navigation.route_types import TravelMode


class RouteWaypointRequestHandlerIf(ABC):
    """Plan and edit routes with intermediate locations."""

    @abstractmethod
    def request_start_route_with_waypoints(
        self,
        destination: GeoPoint,
        waypoints: Sequence[GeoPoint],
        travel_mode: TravelMode,
    ) -> None:
        """Start guidance through ordered intermediate locations.

        @param destination Final route destination.
        @param waypoints Ordered intermediate route locations.
        @param travel_mode Requested route costing mode.
        """
        ...

    @abstractmethod
    def request_add_waypoint(self, waypoint: GeoPoint) -> None:
        """Request addition of an intermediate route location.

        @param waypoint Geographic waypoint to add.
        """
        ...

    @abstractmethod
    def request_remove_waypoint(self, waypoint_index: int) -> None:
        """Request removal of a waypoint by its displayed index.

        @param waypoint_index Zero-based waypoint index.
        """
        ...
