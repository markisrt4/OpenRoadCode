# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose shared application lifecycle policy for orcUi."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from common.resource_cleanup import ResourceCleanup, close_resources
from pathlib import Path

from apps.common.spotify_controller_factory import create_spotify_controller
from apps.launchers.browser_app_factory import BrowserApplicationFactory
from apps.launchers.google_earth_launcher import GoogleEarthLauncher
from apps.orcUi.media_application_service import MediaApplicationService
from apps.orcUi.native_radio_application_service import NativeRadioApplicationService
from config.application_config import ApplicationsConfigParser
from controllers.application_runtime import AppRuntimeManager
from controllers.radio.streaming_radio_controller import StreamingRadioController
from hardware_io.audio.mpv_streaming_audio_player import MpvStreamingAudioPlayer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APPLICATIONS_CONFIG_PATH = PROJECT_ROOT / "config" / "applications.toml"
TERMUX_APPLICATIONS_CONFIG_PATH = PROJECT_ROOT / "config" / "applications.termux.toml"


@dataclass(frozen=True, slots=True)
class OrcUiApplicationRuntime:
    """Managed application services composed for the ORC frontend."""

    manager: AppRuntimeManager
    radio: NativeRadioApplicationService
    streaming_radio: StreamingRadioController
    media: MediaApplicationService
    earth: GoogleEarthLauncher | None = None

    _closed: bool = field(default=False, init=False)

    def start_background_apps(self) -> None:
        """Apply configured external-app policy and start shared media work."""
        self.manager.start_background_apps(_report_background_status)
        self.media.start()

    def close(self) -> None:
        """Close feature services before terminating managed applications."""
        if self._closed:
            return
        object.__setattr__(self, "_closed", True)
        close_resources(
            self.streaming_radio.close, self.media.close, self.radio.close, self.manager.stop_all
        )


def create_orc_ui_application_runtime() -> OrcUiApplicationRuntime:
    """Load platform application policy and compose ORC application services."""
    with ResourceCleanup() as cleanup:
        config = ApplicationsConfigParser(_applications_config_path()).load()
        fallback_display = os.environ.get("DISPLAY", ":1" if _is_termux() else ":0")
        manager = AppRuntimeManager(config, remote_display=fallback_display)

        cleanup.callback(manager.stop_all)
        radio = NativeRadioApplicationService()

        browser_factory = BrowserApplicationFactory(config)
        manager.register("youtube", browser_factory.create("youtube"))
        manager.register("netflix", browser_factory.create("netflix"))
        earth_config = config.app("google_earth")
        earth = (
            GoogleEarthLauncher(browser=browser_factory.create("google_earth"))
            if earth_config.enabled
            else None
        )
        if earth is not None:
            manager.register("google_earth", earth)

        cleanup.callback(radio.close)
        streaming_radio = StreamingRadioController(MpvStreamingAudioPlayer())
        cleanup.callback(streaming_radio.close)
        media = MediaApplicationService(create_spotify_controller())
        cleanup.callback(media.close)
        runtime = OrcUiApplicationRuntime(
            manager=manager,
            radio=radio,
            streaming_radio=streaming_radio,
            media=media,
            earth=earth,
        )
        cleanup.release()
        return runtime


def _applications_config_path() -> Path:
    override = os.getenv("OPENROAD_APPLICATIONS_CONFIG")
    if override:
        return Path(override).expanduser()
    return TERMUX_APPLICATIONS_CONFIG_PATH if _is_termux() else APPLICATIONS_CONFIG_PATH


def _is_termux() -> bool:
    prefix = os.getenv("PREFIX", "")
    return bool(os.getenv("TERMUX_VERSION")) or prefix.startswith("/data/data/com.termux/")


def _report_background_status(detail: str) -> None:
    print(f"[ApplicationRuntime] {detail}")
