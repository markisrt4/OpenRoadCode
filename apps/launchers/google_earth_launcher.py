# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from apps.launchers.app_launcher_if import StatusCallback
from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.launchers.chromium_devtools_client import ChromiumDevToolsClient, DevToolsTarget


class GoogleEarthLauncher:
    BASE_URL = "https://earth.google.com/web/search"
    WINDOW_CLASS = "openroadcode-google-earth"
    MENU_SHORTCUT = "ctrl+shift+b"
    DEVTOOLS_PORT = 9223

    def __init__(self, *, browser: BrowserKioskLauncher | None = None) -> None:
        self._browser = browser or BrowserKioskLauncher(
            url=self._location_url(42.3314, -83.0458),
            process_pattern="earth.google.com",
            window_class=self.WINDOW_CLASS,
            profile_path="~/.cache/openroadcode/google-earth-chromium",
            extra_arguments=(
                f"--remote-debugging-port={self.DEVTOOLS_PORT}",
                "--remote-debugging-address=127.0.0.1",
            ),
        )
        self._devtools = ChromiumDevToolsClient(port=self.DEVTOOLS_PORT)

    def configure_app_window(self, *, position: tuple[int, int], size: tuple[int, int], parent_window_id: int | None = None) -> None:
        del parent_window_id
        self._browser.configure_app_window(position=position, size=size)

    def configure_fullscreen(self, *, position: tuple[int, int], size: tuple[int, int]) -> None:
        self._browser.configure_kiosk_window(position=position, size=size)

    def configure_kiosk_window(self, *, position: tuple[int, int], size: tuple[int, int]) -> None:
        self.configure_fullscreen(position=position, size=size)

    def set_color_scheme(self, value: str | None) -> None:
        self._browser.set_color_scheme(value)

    def set_location(self, latitude: float, longitude: float) -> None:
        self._browser.set_url(self._location_url(latitude, longitude))

    def toggle_menu_bar(self, display: str) -> bool:
        return self._browser.send_key(display, self.MENU_SHORTCUT)

    def devtools_target(self) -> DevToolsTarget | None:
        """Return the live Google Earth page exposed by Chromium DevTools."""
        try:
            return self._devtools.earth_target()
        except (OSError, ValueError):
            return None

    def devtools_available(self) -> bool:
        return self.devtools_target() is not None

    def launch(self, display: str, set_status: StatusCallback = None) -> None:
        self._browser.launch(display, set_status)

    def show(self, display: str, set_status: StatusCallback = None) -> bool:
        return self._browser.show(display, set_status)

    def hide(self, display: str, set_status: StatusCallback = None) -> bool:
        return self._browser.hide(display, set_status)

    def stop(self, display: str, set_status: StatusCallback = None) -> None:
        self._browser.stop(display, set_status)

    def toggle(self, display: str, set_status: StatusCallback = None) -> bool:
        return self._browser.toggle(display, set_status)

    def is_running(self) -> bool:
        return self._browser.is_running()

    @classmethod
    def _location_url(cls, latitude: float, longitude: float, *, tilt: float = 60.0) -> str:
        return f"{cls.BASE_URL}/{latitude},{longitude}/@{latitude},{longitude},182a,605d,35y,0h,{tilt}t,0r"
