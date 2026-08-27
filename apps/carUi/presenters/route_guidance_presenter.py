# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Translate route-guidance bus messages into the UI contract."""

from messaging.contracts.route_guidance import RouteGuidanceStateMessage
from ui.navigation.route_guidance_ui_if import RouteGuidanceUiIf


class RouteGuidancePresenter:
    """Present decoded route-guidance messages to a toolkit-neutral UI."""

    def __init__(self, ui: RouteGuidanceUiIf) -> None:
        self._ui = ui

    def set_guidance_message(self, message: RouteGuidanceStateMessage) -> None:
        data = message.data
        self._ui.set_instruction(data.instruction)
        self._ui.set_distance_to_maneuver(data.distance_to_maneuver_m)
        self._ui.set_distance_remaining(data.distance_remaining_m)
        self._ui.set_off_route(data.off_route)
        self._ui.set_route_complete(data.route_complete)
