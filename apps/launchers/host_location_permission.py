# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Open compact host geolocation consent, preserving a default-browser fallback."""

import os
import webbrowser
import time
import shutil
from threading import Lock
from collections.abc import Callable
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener
from apps.launchers.host_location_session import HostLocationSessionError
from apps.launchers.browser_launcher import BrowserKioskLauncher
from common.xdg_paths import openroadcode_data_dir


class HostLocationPermission:
    @property
    def available(self) -> bool:
        """Termux obtains location through its Android bridge, not this page."""
        return not (os.environ.get("TERMUX_VERSION")
                    or os.environ.get("PREFIX", "").startswith("/data/data/com.termux/"))

    def __init__(self, port: int | None = None, *, recover: Callable[[], None] | None = None) -> None:
        port = port if port is not None else int(os.environ.get("OPENROADCODE_BROWSER_POSITION_PORT", "8765"))
        if not 1 <= port <= 65535:
            raise ValueError("Host location port must be between 1 and 65535")
        self.url = f"http://127.0.0.1:{port}/"
        self._recover = recover
        self._browser = None
        self._browser_lock = Lock()

    def _open_browser(self, cancelled):
        with self._browser_lock:
            if not cancelled():
                self._open_browser_once()

    def _open_browser_once(self):
        candidates = ('google-chrome', 'chromium', 'chromium-browser')
        if os.environ.get('DISPLAY') and any(shutil.which(name) for name in candidates):
            if self._browser is None:
                self._browser = BrowserKioskLauncher(
                    url=self.url, browser_candidates=candidates, kiosk=False, app_mode=True,
                    process_pattern=r'(^|[[:space:]])--class=openroadcode-host-location([[:space:]]|$)',
                    profile_path=openroadcode_data_dir('browser_profiles', 'host-location'),
                    window_class='openroadcode-host-location', window_size=(480, 330),
                    extra_arguments=(
                        '--disable-background-timer-throttling', '--disable-renderer-backgrounding'))
            self._browser.launch(os.environ['DISPLAY'])
            return
        if not webbrowser.open(self.url, new=2):
            raise RuntimeError('Could not open your browser. Set a default browser on this computer, then try again.')

    def open_permission_page(self, cancelled: Callable[[], bool]) -> None:
        if cancelled():
            return
        def check_page():
            # Local permission pages must never be routed through an HTTP proxy.
            with build_opener(ProxyHandler({})).open(self.url, timeout=3) as response:
                page = response.read(32768)
            if b"OpenRoadCode Host Location" not in page:
                raise RuntimeError("Location sharing isn't available with this device's current setup.")
        try:
            check_page()
        except (URLError, OSError) as error:
            if self._recover is None:
                raise RuntimeError("Location sharing couldn't connect. Try again in a moment.") from error
            if cancelled():
                return
            try:
                self._recover()
            except Exception as recovery_error:
                message = (str(recovery_error) if isinstance(recovery_error, HostLocationSessionError)
                           else 'Location sharing could not start. Please retry or check ORC diagnostics.')
                raise RuntimeError(message) from recovery_error
            deadline = time.monotonic() + 5
            while not cancelled():
                try:
                    check_page()
                    break
                except (URLError, OSError) as retry_error:
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Location sharing couldn't connect. Please try again.") from retry_error
                    time.sleep(0.2)
        if cancelled():
            return
        self._open_browser(cancelled)
