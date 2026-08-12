# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from apps.launchers.app_launcher_if import (
    AppLauncherIf,
    StatusCallback,
)
from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.launchers.process_manager import (
    close_matching_display_apps,
    is_process_running,
)
from common.logging.logging_paths import logging_file_path


class ADSBLauncher(AppLauncherIf):
    """Launch readsb and the tar1090 browser dashboard."""

    def __init__(
        self,
        *,
        url: str = "http://127.0.0.1/tar1090",
        browser_log_file: str | Path | None = None,
        close_existing_display_apps: bool = False,
        resource_manager=None,
        owner_name: str = "adsb",
        readsb_service: str = "readsb",
        startup_timeout_seconds: float = 5.0,
    ) -> None:
        self.url = url
        self.close_existing_display_apps = close_existing_display_apps
        self.resource_manager = resource_manager
        self.owner_name = owner_name
        self.readsb_service = readsb_service
        self.startup_timeout_seconds = startup_timeout_seconds
        self.browser = BrowserKioskLauncher(
            url=url,
            process_pattern="127.0.0.1/tar1090",
            profile_path=(
                Path.home()
                / "snap"
                / "chromium"
                / "common"
                / "openroadcode-adsb"
            ),
            window_class="OpenRoadCodeADSB",
            exclusive_group="openroadcode-auxiliary-dashboard",
            log_file=(
                browser_log_file
                or logging_file_path(
                    "openroadcode",
                    "adsb-browser.log",
                )
            ),
        )

    def is_running(self) -> bool:
        return self.browser.is_running()

    def configure_browser_window(
        self,
        *,
        position: tuple[int, int],
        size: tuple[int, int],
    ) -> None:
        """Align the tar1090 browser to a Car UI panel."""
        self.browser.configure_app_window(
            position=position,
            size=size,
        )

    def launch(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        _status(set_status, "Launching ADS-B dashboard...")

        if self.resource_manager is not None:
            self.resource_manager.acquire(
                self.owner_name,
                force=True,
                set_status=set_status,
            )

        if self.close_existing_display_apps:
            close_matching_display_apps(
                display=remote_display,
                patterns=("sdrpp", "sdr\\+\\+"),
            )

        subprocess.run(
            ["sudo", "systemctl", "start", self.readsb_service],
            check=False,
        )

        receiver_ready = self._readsb_is_running()
        dashboard_ready = self._dashboard_is_reachable()
        if not dashboard_ready:
            receiver_ready = self._wait_for_readsb()
            dashboard_ready = self._dashboard_is_reachable()
        if not dashboard_ready:
            raise RuntimeError(
                f"{self.readsb_service} failed to start and the "
                "tar1090 dashboard is unavailable"
            )
        if not receiver_ready:
            _status(
                set_status,
                "ADS-B receiver unavailable; opening dashboard without live data",
            )

        self.browser.launch(remote_display, set_status)
        _status(set_status, "ADS-B dashboard launched")

    def stop(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        self.browser.stop(remote_display, None)
        _status(set_status, "ADS-B dashboard closed")

    def toggle(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> bool:
        if self.is_running():
            self.stop(remote_display, set_status)
            return False

        self.launch(remote_display, set_status)
        return True

    def _wait_for_readsb(self) -> bool:
        deadline = time.monotonic() + self.startup_timeout_seconds
        while time.monotonic() < deadline:
            if self._readsb_is_running():
                return True
            time.sleep(0.25)
        return False

    def _readsb_is_running(self) -> bool:
        return is_process_running(
            rf"(^|/){self.readsb_service}( |$)"
        )

    def _dashboard_is_reachable(self) -> bool:
        try:
            with urlopen(self.url, timeout=2.0) as response:
                return 200 <= response.status < 400
        except (OSError, URLError, ValueError):
            return False


def _status(callback: StatusCallback, message: str) -> None:
    if callback is not None:
        callback(message)
