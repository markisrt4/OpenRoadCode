# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Google Earth browser launcher for geographic visualization."""

from __future__ import annotations

from apps.launchers.app_launcher_if import StatusCallback
from apps.launchers.browser_launcher import BrowserKioskLauncher


class GoogleEarthLauncher:
    """Present Google Earth centered on a requested geographic location."""

    BASE_URL = "https://earth.google.com/web/search"

    def __init__(self, *, browser: BrowserKioskLauncher | None = None) -> None:
        self._browser = browser or BrowserKioskLauncher(
            url=self._location_url(42.3314, -83.0458),
            process_pattern="earth.google.com",
            window_class="openroadcode-google-earth",
        )

    def configure_app_window(
        self,
        *,
        position: tuple[int, int],
        size: tuple[int, int],
    ) -> None:
        """Present Earth as a positioned Chromium app window."""
        self._browser.configure_app_window(position=position, size=size)

    def set_location(self, latitude: float, longitude: float) -> None:
        """Set the location used by the next Google Earth launch."""
        self._browser.set_url(self._location_url(latitude, longitude))

    def focus_location(
        self,
        latitude: float,
        longitude: float,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        """Restart Google Earth centered on a new location."""
        if self.is_running():
            self.stop(remote_display)
        self.set_location(latitude, longitude)
        self.launch(remote_display, set_status)

    def launch(self, remote_display: str, set_status: StatusCallback = None) -> None:
        self._browser.launch(remote_display, set_status)

    def show(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        return self._browser.show(remote_display, set_status)

    def hide(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        return self._browser.hide(remote_display, set_status)

    def stop(self, remote_display: str, set_status: StatusCallback = None) -> None:
        self._browser.stop(remote_display, set_status)

    def toggle(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        return self._browser.toggle(remote_display, set_status)

    def is_running(self) -> bool:
        return self._browser.is_running()

    @classmethod
    def _location_url(
        cls,
        latitude: float,
        longitude: float,
        *,
        tilt: float = 60.0,
    ) -> str:
        return (
            f"{cls.BASE_URL}/{latitude},{longitude}"
            f"/@{latitude},{longitude},"
            f"182a,605d,35y,0h,{tilt}t,0r"
        )
