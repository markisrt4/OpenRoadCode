# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Open host geolocation consent with the system's normal browser, including Firefox."""

import os
import shutil
import subprocess
import time
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from controllers.navigation.host_location_permission_if import (
    HostLocationServiceUnavailable,
)


class HostLocationPermission:
    @property
    def available(self) -> bool:
        """Termux obtains location through its Android bridge, not this page."""
        return not (os.environ.get("TERMUX_VERSION")
                    or os.environ.get("PREFIX", "").startswith("/data/data/com.termux/"))

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
            raise HostLocationServiceUnavailable from error
        if cancelled():
            return
        self._open_browser()

    def _open_browser(self) -> None:
        """Open consent without inheriting OpenCV's private Qt plugin path."""
        browser = next(
            (
                path
                for name in ("google-chrome", "chromium", "chromium-browser", "firefox")
                if (path := shutil.which(name)) is not None
            ),
            None,
        )
        if browser is None:
            raise RuntimeError(f"No supported browser was found. Open {self.url} manually.")
        environment = os.environ.copy()
        environment.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
        environment.pop("QT_QPA_FONTDIR", None)
        try:
            subprocess.Popen(
                [browser, "--new-window", self.url],
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as error:
            raise RuntimeError(f"Could not open the browser. Open {self.url} manually.") from error

    def restart_location_service(self, cancelled: Callable[[], bool]) -> None:
        """Restart navigation through its restricted localhost control plane."""
        if cancelled():
            return
        manager_url = os.environ.get(
            "OPENROADCODE_SERVICE_MANAGER_URL", "http://127.0.0.1:8769"
        ).rstrip("/")
        request = Request(
            manager_url + "/services/openroadcode-navigation/restart",
            data=b"",
            method="POST",
        )
        try:
            with build_opener(ProxyHandler({})).open(request, timeout=5) as response:
                response.read(32768)
        except HTTPError as error:
            if error.code == 401:
                raise RuntimeError(
                    "Automatic restart is not authorized. Repair the OpenRoadCode service-manager installation."
                ) from error
            raise RuntimeError("The location service could not be restarted.") from error
        except (URLError, OSError) as error:
            raise RuntimeError(
                "Automatic restart is unavailable. Start or repair the OpenRoadCode service manager."
            ) from error

        for _attempt in range(20):
            if cancelled():
                return
            try:
                with build_opener(ProxyHandler({})).open(self.url, timeout=1) as response:
                    if b"OpenRoadCode Host Location" in response.read(32768):
                        return
            except (URLError, OSError):
                pass
            time.sleep(0.25)
        raise RuntimeError("The location service did not become ready after restarting.")
