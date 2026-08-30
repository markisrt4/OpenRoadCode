# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic map request controller for the native renderer."""

from __future__ import annotations

from collections.abc import Callable

from ui.navigation import GeoPoint, MapRequestHandlerIf


class MapRequestHandler(MapRequestHandlerIf):
    """Maintain user-controlled camera state and issue native map commands."""

    def __init__(
        self,
        renderer,
        *,
        center: GeoPoint,
        zoom_level: float = 16.5,
        bearing_rad: float = 0.0,
        pitch_rad: float = 0.0,
        follow_enabled: bool = True,
        on_follow_changed: Callable[[bool], None] | None = None,
    ) -> None:
        self._renderer = renderer
        self._center = center
        self._zoom_level = zoom_level
        self._bearing_rad = bearing_rad
        self._pitch_rad = pitch_rad
        self._follow_enabled = follow_enabled
        self._on_follow_changed = on_follow_changed

    @property
    def follow_enabled(self) -> bool:
        return self._follow_enabled

    def request_recenter(self) -> None:
        self.request_follow(True)
        self._send_camera()

    def request_follow(self, enabled: bool) -> None:
        self._follow_enabled = enabled
        if self._on_follow_changed is not None:
            self._on_follow_changed(enabled)

    def request_center_on(self, position: GeoPoint) -> None:
        self._center = position
        self.request_follow(False)
        self._send_camera()

    def request_pan(self, north_m: float, east_m: float) -> None:
        import math

        earth_radius_m = 6_378_137.0
        latitude_rad = self._center.latitude_rad + north_m / earth_radius_m
        cos_latitude = math.cos(latitude_rad)
        if abs(cos_latitude) < 1.0e-6:
            cos_latitude = math.copysign(1.0e-6, cos_latitude)
        longitude_rad = self._center.longitude_rad + east_m / (
            earth_radius_m * cos_latitude
        )

        self._center = GeoPoint(
            latitude_rad=latitude_rad,
            longitude_rad=longitude_rad,
            altitude_m=self._center.altitude_m,
        )
        self.request_follow(False)
        self._send_camera()

    def request_zoom(self, zoom_level: float) -> None:
        self._zoom_level = zoom_level
        self.request_follow(False)
        self._send_camera()

    def request_bearing(self, bearing_rad: float) -> None:
        self._bearing_rad = bearing_rad
        self.request_follow(False)
        self._send_camera()

    def request_pitch(self, pitch_rad: float) -> None:
        self._pitch_rad = pitch_rad
        self.request_follow(False)
        self._send_camera()

    def request_style(self, style_id: str) -> None:
        # Styles are currently selected by the native renderer configuration.
        # Keep the semantic request in the public contract until runtime style
        # switching is added to the renderer protocol.
        del style_id

    def update_follow_center(self, position: GeoPoint) -> None:
        """Update the authoritative vehicle center without changing mode."""

        self._center = position

    def _send_camera(self) -> None:
        import math

        self._renderer.set_camera(
            latitude=math.degrees(self._center.latitude_rad),
            longitude=math.degrees(self._center.longitude_rad),
            zoom=self._zoom_level,
            bearing=math.degrees(self._bearing_rad),
            pitch=math.degrees(self._pitch_rad),
        )
