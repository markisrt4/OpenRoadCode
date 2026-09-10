# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose the ORC shell with map and state-ingress infrastructure."""

from __future__ import annotations

from dataclasses import dataclass

from apps.orcUi.core_runtime import MapRuntime, StateIngressRuntime
from apps.orcUi.orc_ui_app import OrcUiApp
from controllers.navigation.navigation_route_request_handler import NavigationRouteRequestHandler
from services.navigation.navigation_command_client import NavigationCommandClient


@dataclass(slots=True)
class CoreComposition:
    """Own the shell-facing infrastructure for one ORC UI process."""

    app: OrcUiApp
    map_runtime: MapRuntime
    route_request_handler: NavigationRouteRequestHandler
    state_ingress: StateIngressRuntime

    def start(self) -> None:
        self.state_ingress.start()

    def close(self) -> None:
        try:
            self.state_ingress.close()
        finally:
            self.map_runtime.stop()


def create_core_composition() -> CoreComposition:
    """Create the Tk shell and inject its runtime-facing dependencies."""
    map_runtime = MapRuntime()
    route_request_handler = NavigationRouteRequestHandler(NavigationCommandClient())
    app = OrcUiApp(
        map_runtime=map_runtime,
        route_request_handler=route_request_handler,
    )
    state_ingress = StateIngressRuntime(
        schedule_ui=app.schedule_ui_callback,
        apply_vehicle_state=app.apply_vehicle_state,
        apply_position_state=app.apply_position_state,
        apply_attitude_state=app.apply_attitude_state,
        apply_route_guidance_state=app.apply_route_guidance_state,
    )
    return CoreComposition(
        app=app,
        map_runtime=map_runtime,
        route_request_handler=route_request_handler,
        state_ingress=state_ingress,
    )
