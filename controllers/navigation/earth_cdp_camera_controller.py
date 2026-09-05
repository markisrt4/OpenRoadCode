# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Preferred Google Earth camera controller using Chromium DevTools discovery."""

from __future__ import annotations

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient
from controllers.navigation.earth_camera_controller_if import EarthCameraControllerIf, EarthCameraView


class EarthCdpCameraController(EarthCameraControllerIf):
    """Own the stable CDP boundary while Earth page control is investigated."""

    def __init__(self, client: ChromiumDevToolsClient | None = None) -> None:
        self._client = client or ChromiumDevToolsClient(port=9223)

    @property
    def name(self) -> str:
        return "CDP"

    def available(self) -> bool:
        try:
            return self._client.earth_target() is not None
        except (OSError, ValueError):
            return False

    def set_view(self, view: EarthCameraView) -> bool:
        # Deliberately do not depend on undocumented Earth internals yet.
        # The next experiment will add a CDP Runtime.evaluate transport here
        # once we know which page-level mechanism is sufficiently stable.
        del view
        return False
