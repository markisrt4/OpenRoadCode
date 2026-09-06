# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Launch the ORC Spotify Web Playback SDK proof-of-life browser."""

from __future__ import annotations

import os
import signal
import time
from pathlib import Path

from apps.launchers import BrowserKioskLauncher
from apps.orcUi.spotify_web_player_host import SpotifyWebPlayerHost

WINDOW_CLASS = "OpenRoadCodeSpotifyPlayer"
SPOTIFY_BROWSER_CANDIDATES = (
    "google-chrome-stable",
    "google-chrome",
    "chromium",
    "chromium-browser",
)


def main() -> None:
    display = os.environ.get("DISPLAY", ":1")
    host = SpotifyWebPlayerHost()
    browser = BrowserKioskLauncher(
        url=host.url,
        process_pattern="OpenRoadCodeSpotifyPlayer",
        browser_candidates=SPOTIFY_BROWSER_CANDIDATES,
        kiosk=False,
        app_mode=True,
        profile_path=Path.home() / ".cache" / "openroadcode" / "spotify-player-browser",
        window_position=(120, 100),
        window_size=(720, 420),
        startup_grace_seconds=0.5,
        extra_arguments=("--autoplay-policy=no-user-gesture-required",),
        window_class=WINDOW_CLASS,
    )
    stopping = False

    def stop(_signum: int | None = None, _frame: object | None = None) -> None:
        nonlocal stopping
        if stopping:
            return
        stopping = True
        try:
            browser.stop(display)
        finally:
            host.close()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    host.start()
    print(f"[Spotify Player] host {host.url}")
    browser.launch(display)
    print("[Spotify Player] waiting for SDK device registration...")
    try:
        while not stopping:
            if host.device_id:
                print(f"[Spotify Player] SUCCESS: OpenRoadCode device {host.device_id}")
                print("[Spotify Player] Check Spotify Connect on your phone for 'OpenRoadCode'.")
                while not stopping:
                    time.sleep(1.0)
                break
            if host.error:
                print(f"[Spotify Player] SDK error: {host.error}")
            time.sleep(0.5)
    finally:
        stop()


if __name__ == "__main__":
    main()
