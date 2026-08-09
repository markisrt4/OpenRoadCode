"""Semantic requests emitted by a route-guidance UI."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from ui.navigation.map_ui_if import GeoPoint
from ui.navigation.route_guidance_ui_if import TravelMode


class RouteRequestHandlerIf(ABC):
    """Handle route planning and guidance requests."""

    @abstractmethod
    def request_start_route(
        self,
        destination: GeoPoint,
        waypoints: Sequence[GeoPoint],
        travel_mode: TravelMode,
    ) -> None:
        """Request route calculation and guidance.

        @param destination Requested final destination.
        @param waypoints Ordered intermediate route locations.
        @param travel_mode Requested route costing mode.
        """
        ...

    @abstractmethod
    def request_cancel_route(self) -> None:
        """Request cancellation of active route guidance."""
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

    @abstractmethod
    def request_select_alternative(self, alternative_index: int) -> None:
        """Request selection of an alternative route.

        @param alternative_index Zero-based alternative-route index.
        """
        ...

    @abstractmethod
    def request_recalculate_route(self) -> None:
        """Request immediate route recalculation from current position."""
        ...

    @abstractmethod
    def request_travel_mode(self, travel_mode: TravelMode) -> None:
        """Request a new route costing mode.

        @param travel_mode Requested travel mode.
        """
        ...

    @abstractmethod
    def request_voice_guidance_muted(self, muted: bool) -> None:
        """Request spoken route guidance mute state.

        @param muted True to mute spoken route guidance.
        """
        ...
