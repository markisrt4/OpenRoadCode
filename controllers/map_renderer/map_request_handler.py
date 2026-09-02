# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic map request controller for the native renderer."""

from __future__ import annotations

import math
from collections.abc import Callable

from ui.navigation import GeoPoint, MapRequestHandlerIf

_MIN_POI_FOCUS_ZOOM = 14.0


class MapRequestHandler(MapRequestHandlerIf):
    """Maintain user-controlled camera state and issue native map commands."""

    def __init__(self, renderer, *, center: GeoPoint, zoom_level: float = 16.5,
                 bearing_rad: float = 0.0, pitch_rad: float = 0.0,
                 follow_enabled: bool = True,
                 camera_initialized: bool = True,
                 on_follow_changed: Callable[[bool], None] | None = None) -> None:
        self._renderer = renderer
        self._center = center
        self._follow_center = center
        self._zoom_level = zoom_level
        self._bearing_rad = bearing_rad
        self._pitch_rad = pitch_rad
        self._follow_enabled = follow_enabled
        self._camera_initialized = camera_initialized
        self._poi_focus: set[str] = set()
        self._on_follow_changed = on_follow_changed

    @property
    def follow_enabled(self) -> bool:
        return self._follow_enabled

    @property
    def camera_initialized(self) -> bool:
        return self._camera_initialized

    @property
    def zoom_level(self) -> float:
        return self._zoom_level

    @property
    def bearing_rad(self) -> float:
        return self._bearing_rad

    @property
    def pitch_rad(self) -> float:
        return self._pitch_rad

    @property
    def poi_focus(self) -> frozenset[str]:
        return frozenset(self._poi_focus)

    def request_recenter(self) -> None:
        self._center = self._follow_center
        self.request_follow(True)
        self._send_camera()

    def request_follow(self, enabled: bool) -> None:
        self._follow_enabled = enabled
        if enabled:
            self._center = self._follow_center
        if self._on_follow_changed is not None:
            self._on_follow_changed(enabled)

    def request_center_on(self, position: GeoPoint) -> None:
        self._center = position
        self._camera_initialized = True
        self.request_follow(False)
        self._send_camera()

    def request_pan(self, north_m: float, east_m: float) -> None:
        self._pan_geographic(north_m=north_m, east_m=east_m)

    def request_pan_screen(self, right_px: float, up_px: float) -> None:
        earth_circumference_m = 2.0 * math.pi * 6_378_137.0
        metres_per_pixel = (earth_circumference_m * max(0.01, math.cos(self._center.latitude_rad))
                            / (512.0 * (2.0**self._zoom_level)))
        screen_right_m = right_px * metres_per_pixel
        screen_up_m = up_px * metres_per_pixel
        cos_bearing = math.cos(self._bearing_rad)
        sin_bearing = math.sin(self._bearing_rad)
        self._pan_geographic(
            north_m=screen_up_m * cos_bearing - screen_right_m * sin_bearing,
            east_m=screen_up_m * sin_bearing + screen_right_m * cos_bearing,
        )

    def request_zoom(self, zoom_level: float) -> None:
        self._zoom_level = zoom_level
        self._send_camera()

    def request_bearing(self, bearing_rad: float) -> None:
        self._bearing_rad = bearing_rad
        self.request_follow(False)
        self._send_camera()

    def request_pitch(self, pitch_rad: float) -> None:
        self._pitch_rad = pitch_rad
        self.request_follow(False)
        self._send_camera()

    def request_poi_focus(self, category: str | None) -> None:
        if category is None:
            for active in tuple(self._poi_focus):
                self._renderer.set_poi_focus(active, False)
            self._poi_focus.clear()
            return
        enabled = category not in self._poi_focus
        if enabled:
            self._poi_focus.add(category)
            if self._zoom_level < _MIN_POI_FOCUS_ZOOM:
                self._zoom_level = _MIN_POI_FOCUS_ZOOM
                self._send_camera()
        else:
            self._poi_focus.remove(category)
        self._renderer.set_poi_focus(category, enabled)

    def request_style(self, style_id: str) -> None:
        del style_id

    def request_fit_bounds(self, south: float, west: float, north: float, east: float,
                           padding: float = 60.0) -> None:
        """Frame explicit bounds and suspend follow so the result stays visible."""
        self.request_follow(False)
        self._renderer.fit_bounds(south, west, north, east, padding)

    def request_dataset_overview(self, padding: float = 24.0) -> None:
        """Frame the installed offline dataset without inventing a position."""
        self._renderer.fit_dataset(padding)

    def refresh_renderer_state(
        self,
        *,
        zoom_level: float | None = None,
        bearing_rad: float | None = None,
        pitch_rad: float | None = None,
    ) -> None:
        """Replay state, optionally with a non-persistent presentation camera."""
        self._send_camera(
            zoom_level=zoom_level,
            bearing_rad=bearing_rad,
            pitch_rad=pitch_rad,
        )
        for category in self._poi_focus:
            self._renderer.set_poi_focus(category, True)

    def update_follow_center(self, position: GeoPoint) -> None:
        self.update_follow_camera(position)

    def update_follow_bearing(self, bearing_rad: float) -> None:
        if not self._follow_enabled:
            return
        self._bearing_rad = bearing_rad
        self._send_camera()

    def update_follow_camera(
        self,
        position: GeoPoint,
        bearing_rad: float | None = None,
    ) -> None:
        self._follow_center = position
        self._camera_initialized = True
        if not self._follow_enabled:
            return
        self._center = position
        if bearing_rad is not None:
            self._bearing_rad = bearing_rad
        self._send_camera()

    def _pan_geographic(self, *, north_m: float, east_m: float) -> None:
        if not self._camera_initialized:
            return
        earth_radius_m = 6_378_137.0
        latitude_rad = self._center.latitude_rad + north_m / earth_radius_m
        cos_latitude = math.cos(latitude_rad)
        if abs(cos_latitude) < 1.0e-6:
            cos_latitude = math.copysign(1.0e-6, cos_latitude)
        longitude_rad = self._center.longitude_rad + east_m / (earth_radius_m * cos_latitude)
        self._center = GeoPoint(latitude_rad=latitude_rad, longitude_rad=longitude_rad,
                                altitude_m=self._center.altitude_m)
        self.request_follow(False)
        self._send_camera()

    def _send_camera(
        self,
        *,
        zoom_level: float | None = None,
        bearing_rad: float | None = None,
        pitch_rad: float | None = None,
    ) -> None:
        if not self._camera_initialized:
            return
        self._renderer.set_camera(
            latitude=math.degrees(self._center.latitude_rad),
            longitude=math.degrees(self._center.longitude_rad),
            zoom=self._zoom_level if zoom_level is None else zoom_level,
            bearing=math.degrees(self._bearing_rad if bearing_rad is None else bearing_rad),
            pitch=math.degrees(self._pitch_rad if pitch_rad is None else pitch_rad),
        )
