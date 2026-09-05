# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Single background Spotify state/control service for ORC UI."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable

from apps.common.spotify_controller_factory import create_spotify_controller
from controllers.spotify import SpotifyMediaPresenter
from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.spotify.spotify_state import SpotifyState
from ui.media import (
    MediaState,
    MediaUiStub,
    PlaybackRequestHandlerIf,
    SeekRequestHandlerIf,
    TrackRequestHandlerIf,
    VolumeRequestHandlerIf,
)


class _SynchronizedSpotifyController(SpotifyControllerIf):
    """Serialize access to one Spotify controller across ORC worker threads."""

    def __init__(self, backend: SpotifyControllerIf) -> None:
        self._backend = backend
        self._lock = threading.RLock()

    def current_state(self) -> SpotifyState:
        with self._lock:
            return self._backend.current_state()

    def play(self) -> None:
        with self._lock:
            self._backend.play()

    def pause(self) -> None:
        with self._lock:
            self._backend.pause()

    def play_pause(self) -> None:
        with self._lock:
            self._backend.play_pause()

    def next_track(self) -> None:
        with self._lock:
            self._backend.next_track()

    def previous_track(self) -> None:
        with self._lock:
            self._backend.previous_track()

    def set_volume_percent(self, volume_percent: int) -> None:
        with self._lock:
            self._backend.set_volume_percent(volume_percent)

    def seek_to_position_ms(self, position_ms: int) -> None:
        with self._lock:
            self._backend.seek_to_position_ms(position_ms)


class SpotifyStateService(
    PlaybackRequestHandlerIf,
    TrackRequestHandlerIf,
    SeekRequestHandlerIf,
    VolumeRequestHandlerIf,
):
    """Poll Spotify once, cache MediaState, and run controls off the Tk thread."""

    def __init__(self, *, refresh_seconds: float = 2.0) -> None:
        if refresh_seconds <= 0:
            raise ValueError("refresh_seconds must be positive")
        self._controller = _SynchronizedSpotifyController(create_spotify_controller())
        self._presenter = SpotifyMediaPresenter(self._controller, MediaUiStub())
        self._refresh_seconds = refresh_seconds
        self._state = MediaState()
        self._state_lock = threading.Lock()
        self._commands: queue.Queue[Callable[[], None]] = queue.Queue()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def controller(self) -> SpotifyControllerIf:
        """Return the synchronized backend for worker-only integrations."""
        return self._controller

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="orcui-spotify-service",
            daemon=True,
        )
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        self._wake.set()
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)

    def latest_state(self) -> MediaState:
        with self._state_lock:
            return self._state

    def request_refresh(self) -> None:
        """Wake the state worker for an immediate Spotify API refresh."""
        self._wake.set()

    def request_play(self) -> None:
        self._enqueue(self._controller.play)

    def request_pause(self) -> None:
        self._enqueue(self._controller.pause)

    def request_previous_track(self) -> None:
        self._enqueue(self._controller.previous_track)

    def request_next_track(self) -> None:
        self._enqueue(self._controller.next_track)

    def request_rewind(self, seconds: float) -> None:
        state = self.latest_state()
        self.request_seek(max(0.0, (state.position_s or 0.0) - seconds))

    def request_forward(self, seconds: float) -> None:
        state = self.latest_state()
        self.request_seek((state.position_s or 0.0) + seconds)

    def request_seek(self, position_s: float) -> None:
        position_ms = int(max(0.0, position_s) * 1000.0)
        self._enqueue(lambda: self._controller.seek_to_position_ms(position_ms))

    def request_volume(self, volume_percent: int) -> None:
        clamped = max(0, min(100, volume_percent))
        self._enqueue(lambda: self._controller.set_volume_percent(clamped))

    def _enqueue(self, command: Callable[[], None]) -> None:
        self._commands.put(command)
        self._wake.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            self._drain_commands()
            self._refresh_state()
            self._wake.wait(self._refresh_seconds)
            self._wake.clear()

    def _drain_commands(self) -> None:
        while not self._stop.is_set():
            try:
                command = self._commands.get_nowait()
            except queue.Empty:
                return
            try:
                command()
            except Exception as error:
                print(f"WARNING: Spotify command failed: {type(error).__name__}: {error}")

    def _refresh_state(self) -> None:
        try:
            state = self._presenter.read_state()
        except Exception as error:
            # Keep the service alive through transient auth/network failures.
            print(f"WARNING: Spotify state refresh failed: {type(error).__name__}: {error}")
            return
        with self._state_lock:
            self._state = state
