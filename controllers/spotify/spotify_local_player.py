# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent lifecycle for an OpenRoadCode Spotify playback device."""

from __future__ import annotations

import os
import shutil
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from controllers.spotify.spotify_state_service import SpotifyStateService


class SpotifyPlayerHostIf(Protocol):
    """Minimal Web Playback host behavior required by local-player lifecycle."""

    @property
    def url(self) -> str: ...

    @property
    def error(self) -> str | None: ...

    @property
    def device_id(self) -> str | None: ...

    def start(self) -> None: ...

    def close(self) -> None: ...


class SpotifyPlayerBrowserIf(Protocol):
    """Minimal managed-browser behavior required by local-player lifecycle."""

    def launch(self, display: str) -> None: ...

    def hide(self, display: str) -> None: ...

    def stop(self, display: str) -> None: ...


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


HostFactory = Callable[[], SpotifyPlayerHostIf]
BrowserFactory = Callable[[str], SpotifyPlayerBrowserIf]
BrowserFinder = Callable[[str], str | None]


class SpotifyLocalPlayer:
    """Own a Web Playback host/browser pair without depending on any UI toolkit."""

    def __init__(
        self,
        *,
        spotify_service: SpotifyStateService,
        host_factory: HostFactory,
        browser_factory: BrowserFactory,
        browser_candidates: Sequence[str],
        display: str | None = None,
        registration_timeout_seconds: float = 15.0,
        browser_finder: BrowserFinder = shutil.which,
    ) -> None:
        if registration_timeout_seconds <= 0:
            raise ValueError("registration_timeout_seconds must be positive")
        if not browser_candidates:
            raise ValueError("browser_candidates must not be empty")
        self._spotify_service = spotify_service
        self._display = display or os.environ.get("DISPLAY", ":1")
        self._registration_timeout_seconds = registration_timeout_seconds
        self._host_factory = host_factory
        self._browser_factory = browser_factory
        self._browser_candidates = tuple(browser_candidates)
        self._browser_finder = browser_finder
        self._lock = threading.RLock()
        self._generation = 0
        self._host: SpotifyPlayerHostIf | None = None
        self._browser: SpotifyPlayerBrowserIf | None = None
        self._closed = False
        available = self._supported_browser() is not None
        message = (
            "Remote Spotify device control"
            if available
            else "PLAYER requires a supported browser with Spotify Web Playback support"
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
                    message="PLAYER unavailable: install a supported browser",
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
            name="spotify-local-player-start",
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
            name="spotify-local-player-stop",
            daemon=True,
        ).start()

    def close(self) -> None:
        """Stop the browser and SDK host during application shutdown."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._generation += 1
            generation = self._generation
        self._deactivate_player(generation, True)

    def _activate_player(self, generation: int) -> None:
        host: SpotifyPlayerHostIf | None = None
        browser: SpotifyPlayerBrowserIf | None = None
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

    def _supported_browser(self) -> str | None:
        for candidate in self._browser_candidates:
            path = self._browser_finder(candidate)
            if path:
                return path
        return None
