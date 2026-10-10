# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from threading import RLock
from pathlib import Path
import re
import time

from ui.system.app_launcher_if import StatusCallback

from apps.launchers.browser_launcher import BrowserKioskLauncher
from protocols.chromium.chromium_devtools_client import ChromiumDevToolsClient, DevToolsTarget


class GoogleEarthLauncher:
    BASE_URL = "https://earth.google.com/web/search"
    WINDOW_CLASS = "openroadcode-google-earth"
    MENU_SHORTCUT = "ctrl+shift+b"
    DEVTOOLS_PORT = 9223

    def __init__(self, *, browser: BrowserKioskLauncher | None = None) -> None:
        self._lifecycle_lock = RLock()
        self._prepared_shell = False
        self._browser = browser or BrowserKioskLauncher(
            url=self._location_url(42.3314, -83.0458),
            process_pattern="earth.google.com",
            window_class=self.WINDOW_CLASS,
            profile_path="~/.cache/openroadcode/google-earth-chromium",
            kiosk=False,
            app_mode=True,
            window_position=(-20000, -20000),
            window_size=(1024, 600),
            extra_arguments=(
                f"--remote-debugging-port={self.DEVTOOLS_PORT}",
                "--remote-debugging-address=127.0.0.1",
                "--remote-allow-origins=*",
            ),
        )
        if browser is not None:
            self._browser.window_class = self.WINDOW_CLASS
            self._browser.extra_arguments = tuple(argument for argument in self._browser.extra_arguments
                if not argument.startswith("--remote-debugging-")) + (
                f"--remote-debugging-port={self.DEVTOOLS_PORT}",
                "--remote-debugging-address=127.0.0.1",
            )
        if isinstance(self._browser.profile_path, (str, Path)):
            self._browser.process_pattern = re.escape(str(self._browser.profile_path))
        self._devtools = ChromiumDevToolsClient(port=self.DEVTOOLS_PORT)

    def prepare(self, remote_display: str, set_status: StatusCallback = None) -> None:
        """Prepare a blank browser shell before embedding creates Earth surfaces."""
        with self._lifecycle_lock:
            if not self._browser.is_running():
                self._browser.set_color_scheme("dark")
                original_url = self._browser.url
                self._browser.url = "about:blank"
                try:
                    self._browser.launch(remote_display, set_status)
                    self._prepared_shell = True
                finally:
                    self._browser.url = original_url
            if not self._browser.hide(remote_display, set_status):
                raise RuntimeError("Google Earth preload could not hide its window")
            if set_status is not None:
                set_status("Google Earth browser shell prepared")

    def configure_app_window(self, *, position: tuple[int, int], size: tuple[int, int], parent_window_id: int | None = None) -> None:
        del parent_window_id
        with self._lifecycle_lock:
            self._browser.configure_app_window(position=position, size=size)

    def configure_fullscreen(self, *, position: tuple[int, int], size: tuple[int, int]) -> None:
        with self._lifecycle_lock:
            self._browser.configure_kiosk_window(position=position, size=size)

    def configure_kiosk_window(self, *, position: tuple[int, int], size: tuple[int, int]) -> None:
        self.configure_fullscreen(position=position, size=size)

    def set_color_scheme(self, value: str | None) -> None:
        with self._lifecycle_lock:
            self._browser.set_color_scheme(value)

    def set_location(self, latitude: float, longitude: float) -> None:
        with self._lifecycle_lock:
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
        with self._lifecycle_lock:
            self._browser.launch(display, set_status)
            self._load_prepared_shell()

    def show(self, display: str, set_status: StatusCallback = None) -> bool:
        with self._lifecycle_lock:
            self._load_prepared_shell()
            return self._browser.show(display, set_status)

    def _load_prepared_shell(self) -> None:
        if not self._prepared_shell:
            return
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            targets = self._devtools.targets()
            if any("earth.google.com" in target.url for target in targets):
                self._prepared_shell = False
                return
            target = next((target for target in targets if target.url == "about:blank"), None)
            if target is not None:
                result = self._devtools.command(target, "Page.navigate", {"url": self._browser.url})
                if result.get("errorText"):
                    raise RuntimeError(result["errorText"])
                self._prepared_shell = False
                return
            time.sleep(0.05)
        raise RuntimeError("Prepared Google Earth browser did not expose its blank page")

    def hide(self, display: str, set_status: StatusCallback = None) -> bool:
        with self._lifecycle_lock:
            return self._browser.hide(display, set_status)

    def stop(self, display: str, set_status: StatusCallback = None) -> None:
        with self._lifecycle_lock:
            self._browser.stop(display, set_status)

    def toggle(self, display: str, set_status: StatusCallback = None) -> bool:
        with self._lifecycle_lock:
            return self._browser.toggle(display, set_status)

    def is_running(self) -> bool:
        with self._lifecycle_lock:
            return self._browser.is_running()

    @classmethod
    def _location_url(cls, latitude: float, longitude: float, *, tilt: float = 60.0) -> str:
        return f"{cls.BASE_URL}/{latitude},{longitude}/@{latitude},{longitude},182a,605d,35y,0h,{tilt}t,0r"
