# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""DOM/accessibility fallback for Google Earth camera control."""

from __future__ import annotations

from controllers.navigation.earth_camera_controller_if import EarthCameraControllerIf, EarthCameraView


class EarthDomCameraController(EarthCameraControllerIf):
    """Fallback boundary for stable Earth DOM controls, when available."""

    @property
    def name(self) -> str:
        return "DOM"

    def available(self) -> bool:
        return False

    def set_view(self, view: EarthCameraView) -> bool:
        del view
        return False
