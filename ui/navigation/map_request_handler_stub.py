# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op map request handler."""

from ui.navigation.map_request_handler_if import MapRequestHandlerIf
from ui.navigation.map_ui_if import GeoPoint


class MapRequestHandlerStub(MapRequestHandlerIf):
    """Ignore semantic map requests."""

    def request_follow(self, enabled: bool) -> None:
        pass

    def request_recenter(self) -> None:
        pass

    def request_center_on(self, position: GeoPoint) -> None:
        pass

    def request_zoom(self, zoom_level: float) -> None:
        pass

    def request_bearing(self, bearing_rad: float) -> None:
        pass

    def request_pitch(self, pitch_rad: float) -> None:
        pass

    def request_style(self, style_id: str) -> None:
        pass
