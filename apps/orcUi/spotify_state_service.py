# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Background Spotify state cache shared by ORC UI surfaces."""

from __future__ import annotations

import threading

from apps.common.spotify_controller_factory import create_spotify_controller
from controllers.spotify import SpotifyMediaPresenter
from ui.media import MediaState, MediaUiStub


class SpotifyStateService:
    """Poll Spotify once and expose the latest media snapshot to the UI."""

    def __init__(self, *, refresh_seconds: float = 5.0) -> None:
        if refresh_seconds <= 0:
            raise ValueError("refresh_seconds must be positive")
        self._controller = create_spotify_controller()
        self._presenter = SpotifyMediaPresenter(self._controller, MediaUiStub())
        self._refresh_seconds = refresh_seconds
        self._state = MediaState()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def controller(self):
        return self._controller

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="orcui-spotify-state-service",
            daemon=True,
        )
        self._thread.start()

    def close(self) -> None:
        self._stop_event.set()
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)

    def latest_state(self) -> MediaState:
        with self._lock:
            return self._state

    def refresh_now(self) -> MediaState:
        state = self._presenter.read_state()
        with self._lock:
            self._state = state
        return state

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.refresh_now()
            self._stop_event.wait(self._refresh_seconds)
