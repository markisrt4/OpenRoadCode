# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ADS-B application lifecycle adapter for orcUi."""

from __future__ import annotations

import os
from pathlib import Path

from apps.launchers.adsb_launcher import ADSBLauncher
from config.application_config import ApplicationsConfigParser

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
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
        if launcher is not None:
            self._launcher = launcher
            return
        applications = ApplicationsConfigParser(_applications_path()).load()
        config = applications.app("adsb")
        self._launcher = ADSBLauncher(
            url=config.url or "http://127.0.0.1/tar1090",
            data_source=config.adsb_data_source.value if config.adsb_data_source is not None else "rtlsdr",
        )

    @property
    def running(self) -> bool:
        return self._launcher.is_running()

    def launch(self, display: str) -> None:
        self._launcher.launch(display)

    def stop(self, display: str) -> None:
        self._launcher.stop(display)
