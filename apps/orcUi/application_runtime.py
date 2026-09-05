# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose shared external-application lifecycle policy for orcUi."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from apps.launchers.managed_sdrpp_launcher import ManagedSDRPPLauncher
from apps.launchers.sdrpp_launcher import SDRPPProfile
from config.application_config import ApplicationsConfigParser
from config.radio_config_manager import load_radio_config
from controllers.application_runtime import AppRuntimeManager
from controllers.radio.radio_profiles import RadioProfileCatalog

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APPLICATIONS_CONFIG_PATH = PROJECT_ROOT / "config" / "applications.toml"
TERMUX_APPLICATIONS_CONFIG_PATH = PROJECT_ROOT / "config" / "applications.termux.toml"


@dataclass(frozen=True, slots=True)
class OrcUiApplicationRuntime:
    """Managed external applications composed for the ORC frontend."""

    manager: AppRuntimeManager
    sdrpp: ManagedSDRPPLauncher

    def start_background_apps(self) -> None:
        self.manager.start_background_apps(_report_background_status)

    def close(self) -> None:
        self.manager.stop_all()


def create_orc_ui_application_runtime() -> OrcUiApplicationRuntime:
    """Load platform application policy and register orcUi launchers."""
    config = ApplicationsConfigParser(_applications_config_path()).load()
    fallback_display = os.environ.get("DISPLAY", ":1" if _is_termux() else ":0")
    manager = AppRuntimeManager(config, remote_display=fallback_display)
    sdrpp = ManagedSDRPPLauncher(
        profile=_default_sdrpp_profile(),
        fullscreen=False,
        embedded=True,
    )
    manager.register("sdrpp", sdrpp)
    return OrcUiApplicationRuntime(manager=manager, sdrpp=sdrpp)


def _applications_config_path() -> Path:
    override = os.getenv("OPENROAD_APPLICATIONS_CONFIG")
    if override:
        return Path(override).expanduser()
    return TERMUX_APPLICATIONS_CONFIG_PATH if _is_termux() else APPLICATIONS_CONFIG_PATH


def _default_sdrpp_profile() -> SDRPPProfile:
    catalog = RadioProfileCatalog()
    profile = (
        catalog.profile("fm_radio")
        if any(item.key == "fm_radio" for item in catalog.profiles)
        else catalog.profiles[0]
    )
    config = load_radio_config(profile.config_path)
    start_frequency_hz = (
        config.radio_range.start_frequency_hz
        if config.radio_range is not None
        else None
    )
    return SDRPPProfile(
        name=profile.label,
        mode=config.default_mode.name,
        step_hz=config.default_mode.step_hz,
        start_frequency_hz=start_frequency_hz,
    )


def _is_termux() -> bool:
    prefix = os.getenv("PREFIX", "")
    return bool(os.getenv("TERMUX_VERSION")) or prefix.startswith("/data/data/com.termux/")


def _report_background_status(detail: str) -> None:
    print(f"[ApplicationRuntime] {detail}")
