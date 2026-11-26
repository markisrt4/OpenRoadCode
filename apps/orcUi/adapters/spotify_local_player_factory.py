# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose host-specific adapters for the controller-owned Spotify local player."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from apps.launchers import BrowserKioskLauncher
from apps.orcUi.adapters.spotify_web_player_host import SpotifyWebPlayerHost
from common.xdg_paths import openroadcode_data_dir
from controllers.spotify.spotify_local_player import SpotifyLocalPlayer
from controllers.spotify.spotify_state_service import SpotifyStateService

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
    if (profile / "SingletonSocket").exists():
        raise RuntimeError("Close the ORC Spotify browser before updating protected audio.")
    webprefs["encrypted_media_enabled"] = True
    preferences.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=preferences.parent, delete=False
    ) as output:
        temporary = Path(output.name)
        try:
            json.dump(values, output, ensure_ascii=False)
            output.close()
            temporary.replace(preferences)
        finally:
            temporary.unlink(missing_ok=True)
