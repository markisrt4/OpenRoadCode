# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Google Earth driving follow camera logic."""

from __future__ import annotations

from controllers.navigation.earth_input_camera_controller import EarthInputCameraController


class EarthChaseCameraController:
    """Configure a close oblique driving view and let Earth follow ORC GPS.

    Relative camera rotation looked impressive while parked, but it fights
    Google's own location tracking once the vehicle is moving. Chase mode leaves
    camera centering to the ORC-backed geolocation feed and only applies a
    stable driving perspective.
    """

    _FOLLOW_TILT_STEPS = 6
    _FOLLOW_TILT_STEP_DEG = -5.0

    def __init__(self, input_controller: EarthInputCameraController) -> None:
        self._input = input_controller
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> bool:
        self._enabled = bool(enabled)
        if not self._enabled:
            return True

        # This ordering is deliberate. Runtime testing showed that zooming first
        # and then applying six tilt increments gives the useful ~45 degree view.
        # Reversing the order produces a much lower, near-horizon perspective.
        if not self._input.top_down():
            self._enabled = False
            return False
        if not self._input.north_up():
            self._enabled = False
            return False
        if not self._input.zoom_closest():
            self._enabled = False
            return False
        for _ in range(self._FOLLOW_TILT_STEPS):
            if not self._input.tilt(self._FOLLOW_TILT_STEP_DEG):
                self._enabled = False
                return False
        return True

    def reset_reference(self) -> None:
        """Compatibility hook retained for the navigation panel."""

    def update(self, *, track_rad: float | None, speed_m_s: float | None) -> bool:
        """Do not orbit the camera while driving."""
        del track_rad, speed_m_s
        return False
