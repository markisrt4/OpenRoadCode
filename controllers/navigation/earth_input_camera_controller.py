# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Synthetic-input last resort for Google Earth camera control."""

from __future__ import annotations

from controllers.navigation.earth_camera_controller_if import EarthCameraControllerIf, EarthCameraView


class EarthInputCameraController(EarthCameraControllerIf):
    """Last-resort boundary for browser-local pointer and keyboard input."""

    @property
    def name(self) -> str:
        return "INPUT"

    def available(self) -> bool:
        return False

    def set_view(self, view: EarthCameraView) -> bool:
        del view
        return False
