# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Lifecycle service for OpenRoadCode as a Spotify playback device."""

from __future__ import annotations

import os
import shutil
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from apps.launchers import BrowserKioskLauncher
from apps.orcUi.spotify_state_service import SpotifyStateService
from apps.orcUi.spotify_web_player_host import SpotifyWebPlayerHost

WINDOW_CLASS = "OpenRoadCodeSpotifyPlayer"
SPOTIFY_PLAYER_BROWSERS = ("google-chrome-stable", "google-chrome")


class SpotifyPlaybackMode(str, Enum):
    """User-visible Spotify playback destination mode."""

    REMOTE = "REMOTE"
    PLAYER = "PLAYER"


@dataclass(frozen=True)
class SpotifyLocalPlayerState:
    """Thread-safe snapshot of the local Spotify player lifecycle."""

    mode: SpotifyPlaybackMode = SpotifyPlaybackMode.REMOTE
    available: bool = False
    busy: bool = False
    message: str = "Remote Spotify device control"


HostFactory = Callable[[], SpotifyWebPlayerHost]
BrowserFactory = Callable[[str], BrowserKioskLauncher]


class SpotifyLocalPlayer:
    """Own the SDK host and Chrome process used by Spotify PLAYER mode."""

    def __init__(
        self,
        *,
        spotify_service: SpotifyStateService,
        display: str | None = None,
        registration_timeout_seconds: float = 15.0,
        host_factory: HostFactory = SpotifyWebPlayerHost,
        browser_factory: BrowserFactory | None = None,
    ) -> None:
        if registration_timeout_seconds <= 0:
            raise ValueError("registration_timeout_seconds must be positive")
        self._spotify_service = spotify_service
        self._display = display or os.environ.get("DISPLAY", ":1")
        self._registration_timeout_seconds = registration_timeout_seconds
        self._host_factory = host_factory
        self._browser_factory = browser_factory or self._make_browser
        self._lock = threading.RLock()
        self._generation = 0
        self._host: SpotifyWebPlayerHost | None = None
        self._browser: BrowserKioskLauncher | None = None
        self._closed = False
        available = self._supported_browser() is not None
        message = (
            "Remote Spotify device control"
            if available
            else "PLAYER requires Google Chrome with Spotify Web Playback support"
        )
        self._state = SpotifyLocalPlayerState(available=available, message=message)

    def state(self) -> SpotifyLocalPlayerState:
        """Return the latest local-player state snapshot."""
        with self._lock:
            return self._state

    def request_player(self) -> None:
        """Start the local Spotify player and transfer playback to it."""
        with self._lock:
            if self._closed:
                return
            if not self._state.available:
                self._state = SpotifyLocalPlayerState(
                    mode=SpotifyPlaybackMode.REMOTE,
                    available=False,
                    busy=False,
                    message="PLAYER unavailable: install supported Google Chrome",
                )
                return
            if self._state.mode is SpotifyPlaybackMode.PLAYER and not self._state.busy:
                return
            self._generation += 1
            generation = self._generation
            self._state = SpotifyLocalPlayerState(
                mode=SpotifyPlaybackMode.PLAYER,
                available=True,
                busy=True,
                message="Starting OpenRoadCode Spotify player...",
            )
        threading.Thread(
            target=self._activate_player,
            args=(generation,),
            name="orcui-spotify-local-player-start",
            daemon=True,
        ).start()

    def request_remote(self) -> None:
        """Leave PLAYER mode and release the local Spotify browser backend."""
        with self._lock:
            if self._closed:
                return
            self._generation += 1
            generation = self._generation
            self._state = SpotifyLocalPlayerState(
                mode=SpotifyPlaybackMode.REMOTE,
                available=self._state.available,
                busy=True,
                message="Returning to remote Spotify device control...",
            )
        threading.Thread(
            target=self._deactivate_player,
            args=(generation, False),
            name="orcui-spotify-local-player-stop",
            daemon=True,
        ).start()

    def close(self) -> None:
        """Stop the browser and SDK host during ORC application shutdown."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._generation += 1
            generation = self._generation
        self._deactivate_player(generation, True)

    def _activate_player(self, generation: int) -> None:
        host: SpotifyWebPlayerHost | None = None
        browser: BrowserKioskLauncher | None = None
        try:
            self._stop_runtime()
            host = self._host_factory()
            browser = self._browser_factory(host.url)
            with self._lock:
                if not self._is_current(generation):
                    return
                self._host = host
                self._browser = browser
            host.start()
            browser.launch(self._display)
            deadline = time.monotonic() + self._registration_timeout_seconds
            while time.monotonic() < deadline:
                with self._lock:
                    if not self._is_current(generation):
                        return
                if host.error:
                    raise RuntimeError(host.error)
                device_id = host.device_id
                if device_id:
                    self._spotify_service.request_transfer_playback(device_id, play=True)
                    try:
                        browser.hide(self._display)
                    except (OSError, RuntimeError):
                        pass
                    with self._lock:
                        if self._is_current(generation):
                            self._state = SpotifyLocalPlayerState(
                                mode=SpotifyPlaybackMode.PLAYER,
                                available=True,
                                busy=False,
                                message="Playing on OpenRoadCode",
                            )
                    return
                time.sleep(0.1)
            raise TimeoutError("Spotify Web Player did not register a device in time")
        except Exception as error:
            self._stop_runtime()
            with self._lock:
                if self._is_current(generation):
                    self._state = SpotifyLocalPlayerState(
                        mode=SpotifyPlaybackMode.REMOTE,
                        available=self._supported_browser() is not None,
                        busy=False,
                        message=f"PLAYER failed: {error}",
                    )

    def _deactivate_player(self, generation: int, closing: bool) -> None:
        self._stop_runtime()
        with self._lock:
            if closing or not self._is_current(generation):
                return
            self._state = SpotifyLocalPlayerState(
                mode=SpotifyPlaybackMode.REMOTE,
                available=self._supported_browser() is not None,
                busy=False,
                message="Remote Spotify device control",
            )

    def _stop_runtime(self) -> None:
        with self._lock:
            browser = self._browser
            host = self._host
            self._browser = None
            self._host = None
        if browser is not None:
            try:
                browser.stop(self._display)
            except (OSError, RuntimeError):
                pass
        if host is not None:
            host.close()

    def _is_current(self, generation: int) -> bool:
        return not self._closed and generation == self._generation

    @staticmethod
    def _supported_browser() -> str | None:
        for candidate in SPOTIFY_PLAYER_BROWSERS:
            path = shutil.which(candidate)
            if path:
                return path
        return None

    @staticmethod
    def _make_browser(url: str) -> BrowserKioskLauncher:
        return BrowserKioskLauncher(
            url=url,
            process_pattern=WINDOW_CLASS,
            browser_candidates=SPOTIFY_PLAYER_BROWSERS,
            kiosk=False,
            app_mode=True,
            profile_path=Path.home() / ".cache" / "openroadcode" / "spotify-player-browser",
            window_position=(8, 8),
            window_size=(420, 220),
            startup_grace_seconds=0.5,
            extra_arguments=("--autoplay-policy=no-user-gesture-required",),
            window_class=WINDOW_CLASS,
        )
