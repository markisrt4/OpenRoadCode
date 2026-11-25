# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Route-request adapter from UI contracts to the navigation command service."""

from __future__ import annotations

import math
from concurrent.futures import Future
from threading import Thread
from collections.abc import Callable

from controllers.route_planning.route_planning_types import GeoPoint as RouteGeoPoint
from controllers.route_planning.route_planning_types import RouteResult
from controllers.route_planning.route_planning_types import TravelMode as RouteTravelMode
from controllers.route_planning.route_map_presenter import present_route
from protocols.map_renderer.map_renderer_client import MapRendererClient
from services.navigation.navigation_command_client import NavigationCommandClient
from ui.navigation import GeoPoint, RouteRequestHandlerIf, RouteSimulationRequestHandlerIf
from ui.navigation.async_route_request_if import AsyncRouteRequestIf
from ui.navigation.route_types import TravelMode


class NavigationRouteRequestHandler(
    RouteRequestHandlerIf, RouteSimulationRequestHandlerIf, AsyncRouteRequestIf
):
    """Send semantic UI route requests to the navigation service."""

    def __init__(
        self,
        client: NavigationCommandClient | None = None,
        map_renderer: MapRendererClient | None = None,
    ) -> None:
        self._client = client or NavigationCommandClient()
        self._map_renderer = map_renderer or MapRendererClient()
        self._pending: Future[RouteResult] | None = None
        self._closed = False
        self._active_route: RouteResult | None = None
        self._route_observers: list[Callable[[RouteResult | None], None]] = []

    @property
    def supported_travel_modes(self) -> frozenset[TravelMode]:
        """Expose only modes understood by the navigation command service."""
        return frozenset((TravelMode.AUTO, TravelMode.BICYCLE, TravelMode.PEDESTRIAN))

    @property
    def active_route(self) -> RouteResult | None:
        """Return the most recently started route, or None after cancellation."""
        return self._active_route

    def observe_route(self, observer: Callable[[RouteResult | None], None]) -> None:
        """Receive successful route starts and cancellation events."""
        self._route_observers.append(observer)

    def request_start_route(
        self,
        destination: GeoPoint,
        travel_mode: TravelMode,
    ) -> None:
        self._ensure_idle()
        self._publish_route(self._start_route(destination, travel_mode))

    def _start_route(self, destination: GeoPoint, travel_mode: TravelMode) -> RouteResult:
        if travel_mode not in self.supported_travel_modes:
            raise ValueError(f"Unsupported route travel mode: {travel_mode.name}")
        return self._client.start_route(
            RouteGeoPoint(
                latitude=math.degrees(destination.latitude_rad),
                longitude=math.degrees(destination.longitude_rad),
            ),
            travel_mode=RouteTravelMode[travel_mode.name],
        )

    def _publish_route(self, route: RouteResult) -> None:
        present_route(route, self._map_renderer)
        self._active_route = route
        for observer in tuple(self._route_observers):
            observer(route)

    @property
    def route_start_pending(self) -> bool:
        return self._pending is not None

    def _ensure_idle(self) -> None:
        if self._closed or self.route_start_pending:
            raise RuntimeError("Navigation request unavailable or already pending")

    def request_start_route_async(self, destination: GeoPoint, travel_mode: TravelMode) -> None:
        self._ensure_idle()
        future: Future[RouteResult] = Future()
        self._pending = future

        def work() -> None:
            if not future.set_running_or_notify_cancel():
                return
            try:
                future.set_result(self._start_route(destination, travel_mode))
            except Exception as error:
                future.set_exception(error)

        Thread(target=work, daemon=True, name="navigation-route-start").start()

    def poll_route_start(self) -> bool:
        """Publish completed requests on the owning UI thread."""
        future = self._pending
        if self._closed or future is None or not future.done():
            return False
        self._pending = None
        self._publish_route(future.result())
        return True

    def request_cancel_route(self) -> None:
        self._ensure_idle()
        self._client.cancel_route()
        self._active_route = None
        for observer in tuple(self._route_observers):
            observer(None)
        self._map_renderer.set_route({"type": "FeatureCollection", "features": []})

    def request_start_route_simulation(self, *, time_scale: float = 60.0) -> None:
        self._client.simulate_active_route(time_scale=time_scale)

    def request_stop_route_simulation(self) -> None:
        self._client.stop_route_simulation()

    def close(self) -> None:
        self._closed = True
        if self._pending is not None:
            self._pending.cancel()
            self._pending = None
        self._map_renderer.close()
