# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op route request handler."""

from ui.navigation.map_ui_if import GeoPoint
from ui.navigation.route_request_handler_if import RouteRequestHandlerIf
from ui.navigation.route_types import TravelMode


class RouteRequestHandlerStub(RouteRequestHandlerIf):
    """Ignore route planning and guidance requests."""

    @property
    def supported_travel_modes(self) -> frozenset[TravelMode]:
        return frozenset(TravelMode)

    def request_start_route(
        self,
        destination: GeoPoint,
        travel_mode: TravelMode,
    ) -> None:
        pass

    def request_cancel_route(self) -> None:
        pass
