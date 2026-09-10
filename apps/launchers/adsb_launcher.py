# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Launch and coordinate the ADS-B aircraft dashboard.

The launcher separates presentation from the configured ADS-B data producer.
The ``rtlsdr`` source owns the shared RTL-SDR resource while the dashboard is
open and starts/stops the Linux ``readsb`` service on demand. The ``simulation``
source only requires an already-running tar1090 web presentation and never
manipulates SDR hardware or systemd services.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from apps.launchers.app_launcher_if import AppLauncherIf, StatusCallback
from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.launchers.process_manager import close_matching_display_apps, is_process_running
from common.logging.logging_paths import logging_file_path

RTLSDR_DATA_SOURCE = "rtlsdr"
SIMULATION_DATA_SOURCE = "simulation"


class ADSBLauncher(AppLauncherIf):
    """Launch a configured ADS-B data source and tar1090 dashboard.

    ``rtlsdr`` is the Raspberry Pi/Linux hardware path. It acquires the shared
    SDR resource, closes competing SDR++ windows, and starts ``readsb`` only
    while the ADS-B application owns the receiver. ``simulation`` is the
    hardware-independent path used by Termux presentation testing.
    """

    def __init__(self, *, url: str = "http://127.0.0.1/tar1090", data_source: str = RTLSDR_DATA_SOURCE, browser_log_file: str | Path | None = None, resource_manager=None, owner_name: str = "adsb", readsb_service: str = "readsb", startup_timeout_seconds: float = 5.0) -> None:
        if data_source not in (RTLSDR_DATA_SOURCE, SIMULATION_DATA_SOURCE):
            raise ValueError(f"Unsupported ADS-B data source: {data_source}")
        self.url = url
        self.data_source = data_source
        self.resource_manager = resource_manager
        self.owner_name = owner_name
        self.readsb_service = readsb_service
        self.startup_timeout_seconds = startup_timeout_seconds
        self.browser = BrowserKioskLauncher(url=url, process_pattern=url, profile_path=Path.home() / ".local" / "share" / "openroadcode" / "browser" / "adsb", window_class="OpenRoadCodeADSB", exclusive_group="openroadcode-auxiliary-dashboard", log_file=browser_log_file or logging_file_path("openroadcode", "adsb-browser.log"))

    def is_running(self) -> bool:
        return self.browser.is_running()

    def configure_browser_window(self, *, position: tuple[int, int], size: tuple[int, int]) -> None:
        self.browser.configure_app_window(position=position, size=size)

    def launch(self, remote_display: str, set_status: StatusCallback = None) -> None:
        _status(set_status, "Launching ADS-B dashboard...")
        receiver_ready = False

        if self.data_source == RTLSDR_DATA_SOURCE:
            if self.resource_manager is not None:
                self.resource_manager.acquire(self.owner_name, force=True, set_status=set_status)
            close_matching_display_apps(display=remote_display, patterns=("sdrpp", "sdr\\+\\+"))
            _set_systemd_service_state(self.readsb_service, "start")
            receiver_ready = self._readsb_is_running()

        dashboard_ready = self._dashboard_is_reachable()
        if not dashboard_ready and self.data_source == RTLSDR_DATA_SOURCE:
            receiver_ready = self._wait_for_readsb()
            dashboard_ready = self._dashboard_is_reachable()
        if not dashboard_ready:
            if self.data_source == RTLSDR_DATA_SOURCE and self.resource_manager is not None:
                self.resource_manager.release(self.owner_name, set_status=set_status)
            raise RuntimeError(f"tar1090 dashboard is unavailable at {self.url}")
        if self.data_source == RTLSDR_DATA_SOURCE and not receiver_ready:
            _status(set_status, "ADS-B receiver unavailable; opening dashboard without live data")

        self.browser.launch(remote_display, set_status)
        _status(set_status, "ADS-B dashboard launched")

    def stop(self, remote_display: str, set_status: StatusCallback = None) -> None:
        self.browser.stop(remote_display, None)
        if self.data_source == RTLSDR_DATA_SOURCE:
            _set_systemd_service_state(self.readsb_service, "stop")
            if self.resource_manager is not None:
                self.resource_manager.release(self.owner_name, set_status=set_status)
        _status(set_status, "ADS-B dashboard closed")

    def toggle(self, remote_display: str, set_status: StatusCallback = None) -> bool:
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
        return is_process_running(rf"(^|/){self.readsb_service}( |$)")

    def _dashboard_is_reachable(self) -> bool:
        try:
            with urlopen(self.url, timeout=2.0) as response:
                return 200 <= response.status < 400
        except (OSError, URLError, ValueError):
            return False


def _set_systemd_service_state(service: str, action: str) -> bool:
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        return False
    command = [systemctl, action, service]
    sudo = shutil.which("sudo")
    if sudo is not None:
        command.insert(0, sudo)
    try:
        subprocess.run(command, check=False)
    except OSError:
        return False
    return True


def _status(callback: StatusCallback, message: str) -> None:
    if callback is not None:
        callback(message)
