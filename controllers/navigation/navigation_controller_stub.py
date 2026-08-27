# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Deterministic in-memory navigation controller."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from hardware_io.imu import Vector3

from .motion_calibration import MotionCalibration
from .navigation_controller_if import NavigationControllerIf
from .navigation_state import GroundMotionState, NavigationState, PositionState


class NavigationControllerStub(NavigationControllerIf):
    """Provide configurable navigation state for demos and UI development."""

    def __init__(self, state: NavigationState | None = None) -> None:
        zero = Vector3(0.0, 0.0, 0.0)
        self._state = state or NavigationState(
            timestamp=datetime.now(),
            heading_deg=0.0,
            pitch_deg=0.0,
            roll_deg=0.0,
            acceleration_mps2=zero,
            linear_acceleration_mps2=zero,
            angular_velocity_rad_s=zero,
        )
        self._started = False
        self._calibration: MotionCalibration | None = None

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def is_available(self) -> bool:
        return True

    @property
    def status_message(self) -> str | None:
        return None

    @property
    def calibration(self) -> MotionCalibration | None:
        return self._calibration

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def reset_heading(self, heading_deg: float = 0.0) -> None:
        self._require_started()
        self._state = replace(self._state, heading_deg=heading_deg % 360.0)

    def calibrate_stationary(
        self,
        sample_count: int = 100,
        sample_interval_s: float = 0.01,
    ) -> MotionCalibration:
        self._require_started()
        if sample_count <= 0:
            raise ValueError("sample_count must be greater than zero")
        if sample_interval_s < 0.0:
            raise ValueError("sample_interval_s must not be negative")

        zero = Vector3(0.0, 0.0, 0.0)
        self._calibration = MotionCalibration(
            acceleration_bias_mps2=zero,
            angular_velocity_bias_rad_s=zero,
            sample_count=sample_count,
        )
        return self._calibration

    def update_position_state(self, position_state: PositionState) -> None:
        self._state = replace(self._state, position=position_state)

    def update_gps_state(self, position_state: PositionState) -> None:
        """Compatibility alias for :meth:`update_position_state`."""
        self.update_position_state(position_state)

    def update_ground_motion_state(self, ground_motion_state: GroundMotionState) -> None:
        self._state = replace(self._state, ground_motion=ground_motion_state)

    def read_state(self) -> NavigationState:
        self._require_started()
        return self._state

    def set_state(self, state: NavigationState) -> None:
        """Replace the deterministic state returned by future reads."""
        self._state = state

    def _require_started(self) -> None:
        if not self._started:
            raise RuntimeError("Navigation controller has not been started")
