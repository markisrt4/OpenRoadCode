# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ADS-B application lifecycle adapter for orcUi."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import logging
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from pathlib import Path

from apps.launchers.adsb_launcher import ADSBLauncher
from config.application_config import ApplicationsConfigParser

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_APPLICATIONS = _PROJECT_ROOT / "config" / "applications.toml"
_TERMUX_APPLICATIONS = _PROJECT_ROOT / "config" / "applications.termux.toml"


def _is_termux() -> bool:
    prefix = os.getenv("PREFIX", "")
    return bool(os.getenv("TERMUX_VERSION")) or prefix.startswith("/data/data/com.termux/")


def _applications_path() -> Path:
    override = os.getenv("OPENROAD_APPLICATIONS_CONFIG")
    if override:
        return Path(override).expanduser()
    return _TERMUX_APPLICATIONS if _is_termux() else _DEFAULT_APPLICATIONS


class OrcUiAdsbControl:
    """Keep ADS-B config/lifecycle details out of the Tk radio presentation."""

    WINDOW_CLASS = "OpenRoadCodeADSB"

    def __init__(self, launcher: ADSBLauncher | None = None) -> None:
        self._simulation_tracking = False
        self._stop_thread = None
        if launcher is not None:
            self._launcher = launcher
            return
        applications = ApplicationsConfigParser(_applications_path()).load()
        config = applications.app("adsb")
        url = config.url or "http://127.0.0.1/tar1090"
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query))
        query.setdefault("sidebarWidth", "25%")
        if _is_termux():
            query.setdefault("baseMap", "osm")
            query.setdefault("nowebgl", "1")
        self._launcher = ADSBLauncher(
            url=urlunsplit(parts._replace(query=urlencode(query))),
            data_source=config.adsb_data_source.value if config.adsb_data_source is not None else "rtlsdr",
        )
        if _is_termux():
            # Reparented GPU surfaces have rendered corrupt blocks on Termux:X11.
            self._launcher.browser.extra_arguments += (
                "--use-gl=angle", "--use-angle=swiftshader",
                "--enable-unsafe-swiftshader", "--disable-gpu-compositing",
                "--ozone-platform=x11",
            )

    @property
    def running(self) -> bool:
        return self._launcher.is_running()

    @property
    def simulation(self) -> bool:
        return self._launcher.data_source == "simulation"

    @property
    def tracking(self) -> bool:
        """Return whether the ADS-B receiver service is actively tracking."""
        if self._launcher.data_source != "rtlsdr":
            return self._simulation_tracking
        systemctl = shutil.which("systemctl")
        if systemctl is None:
            return False
        result = subprocess.run(
            [systemctl, "is-active", "--quiet", self._launcher.readsb_service],
            check=False,
        )
        return result.returncode == 0

    @property
    def aircraft_count(self) -> int:
        """Read the current aircraft count from readsb's authoritative output."""
        path = Path("/run/readsb/aircraft.json")
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return 0
        aircraft = document.get("aircraft", [])
        return len(aircraft) if isinstance(aircraft, list) else 0

    def set_tracking(self, enabled: bool) -> bool:
        """Start or stop receiver tracking without opening the dashboard."""
        if self._launcher.data_source != "rtlsdr":
            self._simulation_tracking = bool(enabled)
            return self._simulation_tracking
        if enabled:
            self._launcher.assert_available()
            if self._launcher.resource_manager is not None:
                acquired = self._launcher.resource_manager.acquire(
                    self._launcher.owner_name,
                    force=False,
                )
                if not acquired:
                    return False
            from apps.launchers.adsb_launcher import _set_systemd_service_state
            if not _set_systemd_service_state(self._launcher.readsb_service, "start"):
                if self._launcher.resource_manager is not None:
                    self._launcher.resource_manager.release(self._launcher.owner_name)
                raise RuntimeError(
                    f"systemd unit {self._launcher.readsb_service}.service is unavailable "
                    "or cannot be started without interactive authorization"
                )
            return self.tracking
        from apps.launchers.adsb_launcher import _set_systemd_service_state
        _set_systemd_service_state(self._launcher.readsb_service, "stop")
        if self._launcher.resource_manager is not None:
            self._launcher.resource_manager.release(self._launcher.owner_name)
        return False

    def assert_available(self) -> None:
        """Raise when RF currently has priority over the ADS-B receiver."""
        self._launcher.assert_available()

    def set_preferred_color_scheme(self, scheme: str) -> None:
        """Apply ORC's preferred light/dark scheme to the ADS-B browser."""
        self._launcher.set_preferred_color_scheme(scheme)

    def configure_browser_window(
        self,
        *,
        position: tuple[int, int],
        size: tuple[int, int],
    ) -> None:
        self._launcher.configure_browser_window(position=position, size=size)

    def launch(self, display: str) -> None:
        if self._stop_thread is not None and self._stop_thread.is_alive():
            raise RuntimeError("ADS-B dashboard is still closing; try again shortly")
        self._launcher.launch(display)
        if self._launcher.data_source != "rtlsdr":
            self._simulation_tracking = True

    def stop(self, display: str) -> None:
        """Close browser/service resources without waiting on the Tk thread."""
        if self._stop_thread is not None and self._stop_thread.is_alive():
            return
        self._simulation_tracking = False
        def close():
            try:
                self._launcher.stop(display)
            except (OSError, RuntimeError, ValueError):
                logging.getLogger(__name__).exception("ADS-B cleanup failed")
        # A non-daemon worker finishes cleanup even if ORC exits immediately.
        self._stop_thread = threading.Thread(target=close, name="adsb-close", daemon=False)
        self._stop_thread.start()
