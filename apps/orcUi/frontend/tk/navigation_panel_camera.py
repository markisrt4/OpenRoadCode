# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Camera controls shared by the navigation panel layout and callbacks."""

import math

from protocols.map_renderer.map_poi_source import RawMapCamera
from ui.navigation import GeoPoint


class NavigationCameraControls:
    """Map control behavior on the navigation panel's camera state."""

    def _sync_renderer_camera(self) -> None:
        camera = self._poi_controller.poll_camera_state()
        if not isinstance(camera, RawMapCamera):
            return
        observe = getattr(self._request_handler, "observe_camera", None)
        if observe is not None:
            observe(GeoPoint(math.radians(camera.latitude), math.radians(camera.longitude)),
                    camera.zoom, math.radians(camera.bearing), math.radians(camera.pitch))
        self._zoom_level = camera.zoom
        self._pitch_rad = math.radians(camera.pitch)
        self._zoom_text.set(f"{camera.zoom:.1f}")
        self._dimension_text.set("2D" if camera.pitch > 0 else "3D")

    def _toggle_follow(self) -> None:
        enabled = not self._follow_enabled
        self.set_follow_enabled(enabled)
        self._request_handler.request_follow(enabled)

    def _pan(self, up: float, right: float) -> None:
        self._map_host.update_idletasks()
        self.set_follow_enabled(False)
        self._request_handler.request_pan_screen(
            right_px=right * max(48, self._map_host.winfo_width() * 0.25),
            up_px=up * max(48, self._map_host.winfo_height() * 0.25),
        )
        self._schedule_active_poi_refresh()

    def _change_zoom(self, delta: float) -> None:
        self._sync_renderer_camera()
        self._zoom_level = max(1, min(22, self._zoom_level + delta))
        self._zoom_text.set(f"{self._zoom_level:.1f}")
        self._request_handler.request_zoom(self._zoom_level)
        self._schedule_active_poi_refresh()

    def _change_pitch(self, delta_deg: float) -> None:
        self._sync_renderer_camera()
        pitch_deg = max(0, min(60, math.degrees(self._pitch_rad) + delta_deg))
        self._pitch_rad = math.radians(pitch_deg)
        self.set_follow_enabled(False)
        self._request_handler.request_pitch(self._pitch_rad)
        self._dimension_text.set("2D" if self._pitch_rad > 0 else "3D")

    def _show_3d_view(self) -> None:
        """Tilt and zoom the current viewport around its existing center."""
        self._zoom_level = 17.0
        self._zoom_text.set(f"{self._zoom_level:.1f}")
        self._pitch_rad = math.radians(60.0)
        self.set_follow_enabled(False)
        self._request_handler.request_zoom(self._zoom_level)
        self._request_handler.request_pitch(self._pitch_rad)
        self._dimension_text.set("2D" if self._pitch_rad > 0 else "3D")
        self._schedule_active_poi_refresh()

    def _north_up(self) -> None:
        self.set_follow_enabled(False)
        self._request_handler.request_bearing(0.0)

    def _recenter(self) -> None:
        self.set_follow_enabled(True)
        self._request_handler.request_recenter()

    def _toggle_map_dimension(self) -> None:
        """Switch between an overhead view and the tilted building view."""
        self._sync_renderer_camera()
        if self._pitch_rad <= 0:
            self._show_3d_view()
            return
        self._pitch_rad = 0.0
        self.set_follow_enabled(False)
        self._request_handler.request_pitch(0.0)
        self._dimension_text.set("3D")
        self._schedule_active_poi_refresh()
