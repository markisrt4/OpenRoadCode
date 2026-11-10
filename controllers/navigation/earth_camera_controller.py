# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Fallback orchestration for Google Earth camera controllers."""

from __future__ import annotations

from collections.abc import Iterable

from controllers.navigation.earth_camera_controller_if import EarthCameraControllerIf, EarthCameraView


class EarthCameraController:
    """Try Earth camera mechanisms in preference order."""

    def __init__(self, controllers: Iterable[EarthCameraControllerIf]) -> None:
        self._controllers = tuple(controllers)
        self._active_controller_name: str | None = None

    @property
    def active_controller_name(self) -> str | None:
        """Return the mechanism that most recently controlled Earth."""
        return self._active_controller_name

    def set_view(self, view: EarthCameraView) -> bool:
        """Apply a view through the first available controller that succeeds."""
        self._active_controller_name = None
        for controller in self._controllers:
            try:
                if not controller.available():
                    continue
                if controller.set_view(view):
                    self._active_controller_name = controller.name
                    return True
            except Exception:
                # One browser integration must never prevent the fallback path.
                continue
        return False
