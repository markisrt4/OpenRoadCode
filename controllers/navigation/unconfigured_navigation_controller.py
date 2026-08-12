# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unavailable implementation for systems without navigation sensors."""

from __future__ import annotations

from typing import NoReturn

from .motion_calibration import MotionCalibration
from .navigation_controller_if import NavigationControllerIf
from .navigation_state import GpsState, NavigationState


class UnconfiguredNavigationController(NavigationControllerIf):
    """Report that navigation support has not been configured."""

    def __init__(
        self,
        reason: str = "Navigation sensors are not configured",
    ) -> None:
        self._reason = reason

    @property
    def is_started(self) -> bool:
        return False

    @property
    def is_available(self) -> bool:
        return False

    @property
    def status_message(self) -> str | None:
        return self._reason

    @property
    def calibration(self) -> MotionCalibration | None:
        return None

    def start(self) -> None:
        self._raise_unavailable()

    def stop(self) -> None:
        pass

    def reset_heading(self, heading_deg: float = 0.0) -> None:
        self._raise_unavailable()

    def calibrate_stationary(
        self,
        sample_count: int = 100,
        sample_interval_s: float = 0.01,
    ) -> MotionCalibration:
        self._raise_unavailable()

    def update_gps_state(self, gps_state: GpsState) -> None:
        self._raise_unavailable()

    def read_state(self) -> NavigationState:
        self._raise_unavailable()

    def _raise_unavailable(self) -> NoReturn:
        raise RuntimeError(self._reason)
