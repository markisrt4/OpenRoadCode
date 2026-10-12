# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Camera controls shared by the navigation panel layout and callbacks."""

import math

from ui.navigation.map_platform_if import MapPlatform, ExplorationCameraAction

from ui.navigation.navigation_places_request_handler_if import NavigationCameraState


class NavigationCameraControls:
    """Map control behavior on the navigation panel's camera state."""

    def _terrain_camera(self, action):
        if self._map_platform is None or self._map_platform.state.requested is not MapPlatform.CESIUM:
            return False
        if action is not None:
            self._map_platform.request_camera(ExplorationCameraAction(action))
        return True

    def _sync_renderer_camera(self) -> None:
        if self._terrain_camera(None):
            return
        camera = self._places_handler.poll_camera_state()
        if not isinstance(camera, NavigationCameraState):
            return
        self._zoom_level = camera.zoom
        self._pitch_rad = camera.pitch_rad
        self._zoom_text.set(f"{camera.zoom:.1f}")
        self._dimension_text.set("2D" if camera.pitch_rad > 0 else "3D")

    def _toggle_follow(self) -> None:
        if self._terrain_camera(None):
            self._map_platform.request_follow(not self._map_platform.state.follow_enabled)
            return
        enabled = not self._follow_enabled
        self.set_follow_enabled(enabled)
        self._request_handler.request_follow(enabled)

    def _pan(self, up: float, right: float) -> None:
        action = 'pan-up' if up > 0 else 'pan-down' if up < 0 else 'pan-right' if right > 0 else 'pan-left'
        if self._terrain_camera(action):
            return
        self._map_host.update_idletasks()
        self.set_follow_enabled(False)
        self._request_handler.request_pan_screen(
            right_px=right * max(48, self._map_host.winfo_width() * 0.25),
            up_px=up * max(48, self._map_host.winfo_height() * 0.25),
        )
        self._schedule_active_poi_refresh()

    def _change_zoom(self, delta: float) -> None:
        if self._terrain_camera('zoom-in' if delta > 0 else 'zoom-out'):
            return
        self._sync_renderer_camera()
        self._zoom_level = max(1, min(22, self._zoom_level + delta))
        self._zoom_text.set(f"{self._zoom_level:.1f}")
        self._request_handler.request_zoom(self._zoom_level)
        self._schedule_active_poi_refresh()

    def _change_pitch(self, delta_deg: float) -> None:
        if self._terrain_camera('pitch-up' if delta_deg > 0 else 'pitch-down'):
            return
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
        if self._terrain_camera('north'):
            return
        self.set_follow_enabled(False)
        self._request_handler.request_bearing(0.0)

    def _recenter(self) -> None:
        if self._terrain_camera('recenter'):
            return
        self.set_follow_enabled(True)
        self._request_handler.request_recenter()

    def _toggle_map_dimension(self) -> None:
        """Switch between an overhead view and the tilted building view."""
        if self._terrain_camera('dimension'):
            return
        self._sync_renderer_camera()
        if self._pitch_rad <= 0:
            self._show_3d_view()
            return
        self._pitch_rad = 0.0
        self.set_follow_enabled(False)
        self._request_handler.request_pitch(0.0)
        self._dimension_text.set("3D")
        self._schedule_active_poi_refresh()
