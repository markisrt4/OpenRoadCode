# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Map-presentation adapter backed by the managed Google Earth application."""

from __future__ import annotations

from apps.launchers.app_runtime_manager import AppRuntimeManager
from apps.launchers.google_earth_launcher import GoogleEarthLauncher
from controllers.navigation.map_presentation_if import MapPresentationIf


class GoogleEarthMapPresentation(MapPresentationIf):
    """Present geographic locations through the managed Google Earth launcher."""

    def __init__(self, app_runtime_manager: AppRuntimeManager) -> None:
        self._app_runtime_manager = app_runtime_manager

    def focus_location(
        self,
        latitude: float,
        longitude: float,
        *,
        altitude_m: float | None = None,
    ) -> None:
        """Center Google Earth on a location and present its managed window."""
        del altitude_m  # Google Earth's current URL integration does not use altitude.
        launcher = self._app_runtime_manager.launcher(
            "google_earth",
            GoogleEarthLauncher,
        )
        if launcher.is_running():
            launcher.stop(self._app_runtime_manager.remote_display)
        launcher.set_location(latitude, longitude)
        self._app_runtime_manager.show("google_earth")
