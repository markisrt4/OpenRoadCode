# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Heading-up chase camera logic for Google Earth."""

from __future__ import annotations

import math

from controllers.navigation.earth_input_camera_controller import EarthInputCameraController


class EarthChaseCameraController:
    """Keep Google Earth's camera approximately aligned with vehicle course.

    Google Earth does not expose an absolute camera-bearing API to ORC, so chase
    mode establishes a known north-up reference and then tracks the relative
    rotations that ORC applies through the input controller.
    """

    _MIN_SPEED_M_S = 2.0
    _HEADING_DEADBAND_DEG = 4.0
    _MAX_ROTATION_STEP_DEG = 12.0
    _CHASE_FORWARD_TILT_STEPS = 6
    _CHASE_FORWARD_TILT_STEP_DEG = -5.0

    def __init__(self, input_controller: EarthInputCameraController) -> None:
        self._input = input_controller
        self._enabled = False
        self._camera_heading_deg: float | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> bool:
        self._enabled = bool(enabled)
        self._camera_heading_deg = None
        if not self._enabled:
            return True

        # Establish a deterministic reference, then tilt from straight-down
        # toward the horizon for a forward-looking driving view.
        if not self._input.top_down():
            self._enabled = False
            return False
        if not self._input.north_up():
            self._enabled = False
            return False
        if not self._input.zoom_closest():
            self._enabled = False
            return False
        for _ in range(self._CHASE_FORWARD_TILT_STEPS):
            if not self._input.tilt(self._CHASE_FORWARD_TILT_STEP_DEG):
                self._enabled = False
                return False

        self._camera_heading_deg = 0.0
        return True

    def reset_reference(self) -> None:
        self._camera_heading_deg = None

    def update(self, *, track_rad: float | None, speed_m_s: float | None) -> bool:
        if not self._enabled or track_rad is None:
            return False
        if speed_m_s is not None and speed_m_s < self._MIN_SPEED_M_S:
            return False
        if self._camera_heading_deg is None:
            if not self._input.north_up():
                return False
            self._camera_heading_deg = 0.0

        target_deg = math.degrees(track_rad) % 360.0
        error_deg = self._shortest_delta(self._camera_heading_deg, target_deg)
        if abs(error_deg) < self._HEADING_DEADBAND_DEG:
            return False

        step_deg = max(-self._MAX_ROTATION_STEP_DEG, min(self._MAX_ROTATION_STEP_DEG, error_deg))
        if not self._input.rotate(step_deg):
            return False
        self._camera_heading_deg = (self._camera_heading_deg + step_deg) % 360.0
        return True

    @staticmethod
    def _shortest_delta(current_deg: float, target_deg: float) -> float:
        return (target_deg - current_deg + 180.0) % 360.0 - 180.0
