# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op route-guidance UI implementation."""

from ui.navigation.route_guidance_ui_if import RouteGuidanceUiIf


class RouteGuidanceUiStub(RouteGuidanceUiIf):
    """Ignore route-guidance presentation updates."""

    def set_instruction(self, instruction: str | None) -> None:
        pass

    def set_distance_to_maneuver(self, distance_m: float | None) -> None:
        pass

    def set_distance_remaining(self, distance_m: float | None) -> None:
        pass

    def set_off_route(self, off_route: bool) -> None:
        pass

    def set_route_complete(self, complete: bool) -> None:
        pass
