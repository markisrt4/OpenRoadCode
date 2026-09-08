# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Optional ORC-owned vehicle marker support for Google Earth."""

from __future__ import annotations

from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient


class EarthVehicleOverlay:
    """Disabled vehicle overlay placeholder.

    The experimental CSS vehicle marker was useful while proving the Earth
    integration path, but it is intentionally not rendered for now. Keeping
    this small interface in place avoids coupling the navigation panel to a
    temporary visual implementation and leaves room for a better marker later.
    """

    _ROOT_ID = "orc-earth-vehicle-overlay"

    def __init__(
        self,
        client: ChromiumDevToolsClient | None = None,
        *,
        x_fraction: float = 0.50,
        y_fraction: float = 0.63,
    ) -> None:
        self._client = client or ChromiumDevToolsClient(port=9223)
        self._x_fraction = max(0.05, min(0.95, float(x_fraction)))
        self._y_fraction = max(0.05, min(0.95, float(y_fraction)))

    def install(self) -> bool:
        """Ensure the old experimental marker is absent."""
        return self.remove()

    def remove(self) -> bool:
        try:
            self._client.evaluate_earth(
                f"document.getElementById('{self._ROOT_ID}')?.remove(); true"
            )
            return True
        except (OSError, RuntimeError, ValueError):
            return False

    def update_attitude(
        self,
        *,
        heading_rad: float | None,
        pitch_rad: float | None,
        roll_rad: float | None,
    ) -> bool:
        """No-op while the experimental vehicle overlay is disabled."""
        del heading_rad, pitch_rad, roll_rad
        return True
