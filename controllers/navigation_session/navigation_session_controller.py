# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Coordinate active-route lifecycle and rerouting."""

from __future__ import annotations

from collections.abc import Callable

from controllers.route_guidance import ReroutePolicy, RouteGuidanceController
from controllers.route_guidance.route_guidance_types import RouteGuidanceState
from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteRequest,
    RouteResult,
    TravelMode,
)
from .navigation_session_types import NavigationSessionState

RouteCalculator = Callable[[RouteRequest], RouteResult]
RouteChangedCallback = Callable[[RouteResult], None]


class NavigationSessionController:
    """Own destination context and coordinate route replacement."""

    def __init__(self, route_calculator: RouteCalculator, guidance_controller: RouteGuidanceController, reroute_policy: ReroutePolicy, *, on_route_changed: RouteChangedCallback | None = None) -> None:
        self._route_calculator = route_calculator
        self._guidance_controller = guidance_controller
        self._reroute_policy = reroute_policy
        self._on_route_changed = on_route_changed
        self._state: NavigationSessionState | None = None

    @property
    def state(self) -> NavigationSessionState | None:
        return self._state

    def start(self, request: RouteRequest, *, route: RouteResult | None = None) -> RouteResult:
        active_route = route if route is not None else self._route_calculator(request)
        self._activate_route(destination=request.destination, travel_mode=request.travel_mode, route=active_route)
        self._reroute_policy.reset()
        return active_route

    def cancel(self) -> None:
        self._state = None
        self._reroute_policy.reset()

    def update(self, position: GeoPoint, guidance: RouteGuidanceState) -> RouteResult | None:
        if self._state is None or not self._reroute_policy.update(guidance):
            return None
        request = RouteRequest(position, self._state.destination, self._state.travel_mode)
        try:
            route = self._route_calculator(request)
        except Exception:
            self._reroute_policy.reroute_failed()
            raise
        self._activate_route(destination=self._state.destination, travel_mode=self._state.travel_mode, route=route)
        self._reroute_policy.reroute_completed()
        return route

    def _activate_route(self, *, destination: GeoPoint, travel_mode: TravelMode, route: RouteResult) -> None:
        self._guidance_controller.replace_route(route)
        self._state = NavigationSessionState(destination, travel_mode, route)
        if self._on_route_changed is not None:
            self._on_route_changed(route)
