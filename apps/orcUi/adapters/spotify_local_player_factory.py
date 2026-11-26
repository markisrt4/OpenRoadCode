# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose host-specific adapters for the controller-owned Spotify local player."""

from __future__ import annotations

import json
import os
import re
import socket
from pathlib import Path
from tempfile import NamedTemporaryFile

from apps.launchers import BrowserKioskLauncher
from apps.launchers.process_manager import close_matching_display_apps
from apps.orcUi.adapters.spotify_web_player_host import SpotifyWebPlayerHost
from common.xdg_paths import openroadcode_data_dir
from controllers.spotify.spotify_local_player import SpotifyLocalPlayer
from controllers.spotify.spotify_state_service import SpotifyStateService

SYSTEM_WIDEVINE = Path("/opt/WidevineCdm")
WINDOW_CLASS = "OpenRoadCodeSpotifyPlayer"
SPOTIFY_PLAYER_BROWSERS = ("google-chrome-stable", "google-chrome", "chromium-browser", "chromium")


def create_spotify_local_player(
    spotify_service: SpotifyStateService,
) -> SpotifyLocalPlayer:
    """Create the local Spotify player with ORC host/browser adapters."""
    return SpotifyLocalPlayer(
        spotify_service=spotify_service,
        host_factory=SpotifyWebPlayerHost,
        browser_factory=_make_browser,
        browser_candidates=SPOTIFY_PLAYER_BROWSERS,
    )


def _make_browser(url: str) -> BrowserKioskLauncher:
    profile = openroadcode_data_dir("spotify-player-browser")
    _enable_protected_audio(profile)
    _configure_system_widevine(profile)
    return BrowserKioskLauncher(
        url=url,
        process_pattern=WINDOW_CLASS,
        browser_candidates=SPOTIFY_PLAYER_BROWSERS,
        kiosk=False,
        app_mode=True,
        profile_path=profile,
        startup_grace_seconds=0.5,
        extra_arguments=(
            "--ozone-platform=x11",
            "--no-first-run",
            "--no-default-browser-check",
            "--start-minimized",
            "--autoplay-policy=no-user-gesture-required",
        ),
        window_class=WINDOW_CLASS,
    )


def _enable_protected_audio(profile: Path) -> None:
    """Allow encrypted media in the dedicated Spotify browser profile."""
    preferences = profile / "Default" / "Preferences"
    try:
        values = json.loads(preferences.read_text(encoding="utf-8"))
    except FileNotFoundError:
        values = {}
    webprefs = values.setdefault("webkit", {}).setdefault("webprefs", {})
    if webprefs.get("encrypted_media_enabled") is True:
        return
    _close_profile_browser(profile)
    webprefs["encrypted_media_enabled"] = True
    _write_profile_json(preferences, values)


def _configure_system_widevine(profile: Path) -> None:
    """Tell Chromium about the Raspberry Pi OS CDM in the ORC profile only."""
    library = Path("_platform_specific/linux_arm64/libwidevinecdm.so")
    if not (SYSTEM_WIDEVINE / library).is_file() or not (SYSTEM_WIDEVINE / "manifest.json").is_file():
        return
    hint = profile / "WidevineCdm" / "latest-component-updated-widevine-cdm"
    try:
        existing = Path(json.loads(hint.read_text(encoding="utf-8"))["Path"])
        if existing.is_absolute() and (existing / library).is_file():
            return
    except (OSError, ValueError, KeyError, TypeError):
        pass
    _close_profile_browser(profile)
    _write_profile_json(hint, {"Path": str(SYSTEM_WIDEVINE)})


def _write_profile_json(path: Path, values: dict[str, object]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            json.dump(values, output, ensure_ascii=False)
            output.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def _close_profile_browser(profile: Path) -> None:
    if not _profile_browser_running(profile):
        return
    close_matching_display_apps(
        display=os.environ.get("DISPLAY", ":1"),
        patterns=(re.escape(f"--user-data-dir={profile}") + r"( |$)",),
        delay_seconds=1.0,
    )
    if _profile_browser_running(profile):
        raise RuntimeError("Close the minimized ORC Spotify browser, then retry.")


def _profile_browser_running(profile: Path) -> bool:
    """Tell a listening Chromium singleton from an abandoned socket file."""
    singleton = profile / "SingletonSocket"
    try:
        address = singleton.resolve(strict=True)
    except FileNotFoundError:
        return False
    except (OSError, RuntimeError):
        return True
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(0.25)
        try:
            client.connect(str(address))
        except (FileNotFoundError, ConnectionRefusedError):
            return False
        except OSError:
            # An inaccessible or busy socket is not safe to write through.
            return True
    return True
