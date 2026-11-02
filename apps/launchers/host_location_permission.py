# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Open host geolocation consent with the system's normal browser, including Firefox."""

import os
import webbrowser
import time
from collections.abc import Callable
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


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
                raise RuntimeError("Location sharing isn't set up on this device. Ask your ORC installer to enable it.") from recovery_error
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
        if not webbrowser.open(self.url, new=2):
            raise RuntimeError("Could not open your browser. Set a default browser on this computer, then try again.")
