# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own navigation telemetry, commands, active route sessions, and guidance."""

from __future__ import annotations

import threading
import time

from controllers.navigation.navigation_controller_if import NavigationControllerIf
from controllers.navigation_session.navigation_session_controller import NavigationSessionController
from controllers.route_guidance import ReroutePolicy
from controllers.route_guidance.route_guidance_controller import RouteGuidanceController
from controllers.route_planning.route_planning_controller_if import RoutePlanningControllerIf
from controllers.route_planning.route_planning_types import GeoPoint, RouteRequest, RouteResult
from messaging.contracts.navigation import NavigationStatePublisher
from messaging.contracts.route_guidance import RouteGuidanceStatePublisher
from services.navigation.navigation_command_service import NavigationCommandService
from services.navigation.zeromq_navigation_command_server import (
    DEFAULT_NAVIGATION_COMMAND_ENDPOINT,
    ZeroMqNavigationCommandServer,
)


class NavigationRuntime:
    """Run navigation telemetry and optional turn-by-turn guidance.

    One runtime owns the navigation controller and, when routing is configured,
    the active navigation session. Route commands therefore cannot diverge from
    the position stream that advances guidance and drives rerouting.
    """

    def __init__(
        self,
        controller: NavigationControllerIf,
        publisher,
        *,
        source: str,
        rate_hz: float = 10.0,
        command_endpoint: str = DEFAULT_NAVIGATION_COMMAND_ENDPOINT,
        route_planning_controller: RoutePlanningControllerIf | None = None,
        guidance_controller: RouteGuidanceController | None = None,
    ) -> None:
        if rate_hz <= 0.0:
            raise ValueError("rate_hz must be greater than zero")
        self._controller = controller
        self._state_publisher = NavigationStatePublisher(publisher, source=source)
        self._guidance_publisher = RouteGuidanceStatePublisher(
            publisher,
            source=f"{source}-guidance",
        )
        self._period_s = 1.0 / rate_hz
        self._route_planning_controller = route_planning_controller
        self._guidance_controller = guidance_controller
        self._session_controller: NavigationSessionController | None = None

        if route_planning_controller is not None and guidance_controller is not None:
            self._session_controller = NavigationSessionController(
                route_planning_controller.calculate_route,
                guidance_controller,
                ReroutePolicy(),
            )

        self._command_server = ZeroMqNavigationCommandServer(
            NavigationCommandService(
                controller,
                route_planning_controller=route_planning_controller,
                on_route_started=(
                    self._activate_route if route_planning_controller is not None else None
                ),
                on_route_cancelled=(
                    self._cancel_route if route_planning_controller is not None else None
                ),
            ),
            command_endpoint,
        )
        self._command_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the controller and command server."""
        self._controller.start()
        self._stop_event.clear()
        self._command_thread = threading.Thread(
            target=self._command_server.run,
            name="navigation-command-server",
            daemon=True,
        )
        self._command_thread.start()

    def run(self) -> None:
        """Publish navigation snapshots and advance active guidance."""
        self.start()
        try:
            while not self._stop_event.is_set():
                started = time.monotonic()
                state = self._controller.read_state()
                self._state_publisher.publish(state)
                self._update_guidance(state)
                remaining = self._period_s - (time.monotonic() - started)
                if remaining > 0.0:
                    self._stop_event.wait(remaining)
        finally:
            self.close()

    def close(self) -> None:
        """Stop command handling, cancel guidance, and release the controller."""
        self._stop_event.set()
        self._cancel_route()
        self._command_server.close()
        thread = self._command_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._command_thread = None
        self._controller.stop()

    def _activate_route(self, request: RouteRequest, route: RouteResult) -> None:
        route_planner = self._route_planning_controller
        if route_planner is None:
            raise RuntimeError("route planning is not configured")

        if self._guidance_controller is None:
            self._guidance_controller = RouteGuidanceController(route)

        if self._session_controller is None:
            self._session_controller = NavigationSessionController(
                route_planner.calculate_route,
                self._guidance_controller,
                ReroutePolicy(),
            )

        self._session_controller.start(request, route=route)

    def _cancel_route(self) -> None:
        session = self._session_controller
        if session is not None:
            session.cancel()

    def _update_guidance(self, state) -> None:
        session = self._session_controller
        guidance_controller = self._guidance_controller
        gps = getattr(state, "gps", None)
        if session is None or guidance_controller is None or gps is None or not gps.has_fix:
            return
        if gps.latitude_deg is None or gps.longitude_deg is None:
            return

        position = GeoPoint(
            latitude=gps.latitude_deg,
            longitude=gps.longitude_deg,
        )
        guidance = guidance_controller.update(position)
        self._guidance_publisher.publish(guidance)
        session.update(position, guidance)
