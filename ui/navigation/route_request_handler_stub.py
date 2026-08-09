"""Concrete no-op route request handler."""

from collections.abc import Sequence

from ui.navigation.map_ui_if import GeoPoint
from ui.navigation.route_guidance_ui_if import TravelMode
from ui.navigation.route_request_handler_if import RouteRequestHandlerIf


class RouteRequestHandlerStub(RouteRequestHandlerIf):
    """Ignore route planning and guidance requests."""

    def request_start_route(
        self,
        destination: GeoPoint,
        waypoints: Sequence[GeoPoint],
        travel_mode: TravelMode,
    ) -> None:
        pass

    def request_cancel_route(self) -> None:
        pass

    def request_add_waypoint(self, waypoint: GeoPoint) -> None:
        pass

    def request_remove_waypoint(self, waypoint_index: int) -> None:
        pass

    def request_select_alternative(self, alternative_index: int) -> None:
        pass

    def request_recalculate_route(self) -> None:
        pass

    def request_travel_mode(self, travel_mode: TravelMode) -> None:
        pass

    def request_voice_guidance_muted(self, muted: bool) -> None:
        pass
