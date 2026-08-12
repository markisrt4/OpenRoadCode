# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op route-guidance UI implementation."""

from ui.navigation.route_guidance_ui_if import (
    RouteGuidanceState,
    RouteGuidanceUiIf,
)
from ui.navigation.route_request_handler_if import RouteRequestHandlerIf


class RouteGuidanceUiStub(RouteGuidanceUiIf):
    """Ignore route-guidance state and callback registration."""

    def set_route_guidance(self, state: RouteGuidanceState | None) -> None:
        pass

    def set_route_request_handler(
        self,
        handler: RouteRequestHandlerIf | None,
    ) -> None:
        pass
