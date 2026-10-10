# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Open host geolocation consent with the system's normal browser, including Firefox."""

import os
import webbrowser
from collections.abc import Callable
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


class HostLocationPermission:
    def __init__(self, port: int | None = None) -> None:
        port = port if port is not None else int(os.environ.get("OPENROADCODE_BROWSER_POSITION_PORT", "8765"))
        if not 1 <= port <= 65535:
            raise ValueError("Host location port must be between 1 and 65535")
        self.url = f"http://127.0.0.1:{port}/"

    def open_permission_page(self, cancelled: Callable[[], bool]) -> None:
        if cancelled():
            return
        try:
            # Local permission pages must never be routed through an HTTP proxy.
            with build_opener(ProxyHandler({})).open(self.url, timeout=3) as response:
                page = response.read(32768)
            if b"OpenRoadCode Host Location" not in page:
                raise RuntimeError("Host location service is unavailable. Check the navigation service.")
        except (URLError, OSError) as error:
            raise RuntimeError("Host location service is unavailable. Restart the navigation service.") from error
        if cancelled():
            return
        if not webbrowser.open(self.url, new=2):
            raise RuntimeError(f"Could not open your default browser. Open {self.url} manually.")
