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
from controllers.spotify.spotify_library import SpotifyLibraryTrack, SpotifyPlaylist
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

    def transfer_playback(self, device_id: str, *, play: bool = True) -> None:
        with self._lock:
            self._backend.transfer_playback(device_id, play=play)

    def saved_tracks(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        with self._lock:
            return self._backend.saved_tracks(limit=limit)

    def recently_played(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        with self._lock:
            return self._backend.recently_played(limit=limit)

    def playlists(self, *, limit: int = 20) -> tuple[SpotifyPlaylist, ...]:
        with self._lock:
            return self._backend.playlists(limit=limit)

    def playlist_tracks(self, playlist_id: str, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        with self._lock:
            return self._backend.playlist_tracks(playlist_id, limit=limit)

    def play_track(self, track_uri: str) -> None:
        with self._lock:
            self._backend.play_track(track_uri)


class SpotifyStateService(
    PlaybackRequestHandlerIf,
    TrackRequestHandlerIf,
    SeekRequestHandlerIf,
    VolumeRequestHandlerIf,
):
    """Cache Spotify playback/library state and keep API work off Tk."""

    LIBRARY_WARM_LIMIT = 18

    def __init__(self, *, refresh_seconds: float = 2.0) -> None:
        if refresh_seconds <= 0:
            raise ValueError("refresh_seconds must be positive")
        self._controller = _SynchronizedSpotifyController(create_spotify_controller())
        self._presenter = SpotifyMediaPresenter(self._controller, MediaUiStub())
        self._refresh_seconds = refresh_seconds
        self._state = MediaState()
        self._state_lock = threading.Lock()
        self._library_lock = threading.RLock()
        self._saved_tracks: tuple[SpotifyLibraryTrack, ...] = ()
        self._recent_tracks: tuple[SpotifyLibraryTrack, ...] = ()
        self._playlists: tuple[SpotifyPlaylist, ...] = ()
        self._saved_tracks_loaded = False
        self._recent_tracks_loaded = False
        self._playlists_loaded = False
        self._commands: queue.Queue[Callable[[], None]] = queue.Queue()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._library_thread: threading.Thread | None = None

    @property
    def controller(self) -> SpotifyControllerIf:
        """Return the synchronized backend for worker-only integrations."""
        return self._controller

    def start(self) -> None:
        """Start playback polling and opportunistic media-library warming."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="orcui-spotify-service", daemon=True)
        self._thread.start()
        self._library_thread = threading.Thread(
            target=self._warm_library,
            name="orcui-spotify-library-warm",
            daemon=True,
        )
        self._library_thread.start()

    def close(self) -> None:
        """Stop background Spotify workers."""
        self._stop.set()
        self._wake.set()
        thread = self._thread
        library_thread = self._library_thread
        self._thread = None
        self._library_thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)
        if library_thread is not None and library_thread.is_alive():
            library_thread.join(timeout=0.25)

    def latest_state(self) -> MediaState:
        """Return the latest cached Spotify media state."""
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

    def request_transfer_playback(self, device_id: str, *, play: bool = True) -> None:
        """Queue a Spotify Connect transfer without blocking the UI thread."""
        self._enqueue(lambda: self._controller.transfer_playback(device_id, play=play))

    def request_play_track(self, track_uri: str) -> None:
        """Queue playback of one Spotify library/history track."""
        self._enqueue(lambda: self._controller.play_track(track_uri))

    def cached_saved_tracks(self) -> tuple[SpotifyLibraryTrack, ...] | None:
        """Return warmed saved tracks, or ``None`` before the first load."""
        with self._library_lock:
            return self._saved_tracks if self._saved_tracks_loaded else None

    def cached_recently_played(self) -> tuple[SpotifyLibraryTrack, ...] | None:
        """Return warmed playback history, or ``None`` before the first load."""
        with self._library_lock:
            return self._recent_tracks if self._recent_tracks_loaded else None

    def cached_playlists(self) -> tuple[SpotifyPlaylist, ...] | None:
        """Return warmed playlists, or ``None`` before the first load."""
        with self._library_lock:
            return self._playlists if self._playlists_loaded else None

    def load_saved_tracks(self, *, limit: int = 20, refresh: bool = False) -> tuple[SpotifyLibraryTrack, ...]:
        """Return saved tracks, using warmed data when possible."""
        with self._library_lock:
            if self._saved_tracks_loaded and not refresh and len(self._saved_tracks) >= min(limit, self.LIBRARY_WARM_LIMIT):
                return self._saved_tracks[:limit]
        tracks = self._controller.saved_tracks(limit=limit)
        with self._library_lock:
            self._saved_tracks = tracks
            self._saved_tracks_loaded = True
        return tracks

    def load_recently_played(self, *, limit: int = 20, refresh: bool = False) -> tuple[SpotifyLibraryTrack, ...]:
        """Return recent tracks, using warmed data when possible."""
        with self._library_lock:
            if self._recent_tracks_loaded and not refresh and len(self._recent_tracks) >= min(limit, self.LIBRARY_WARM_LIMIT):
                return self._recent_tracks[:limit]
        tracks = self._controller.recently_played(limit=limit)
        with self._library_lock:
            self._recent_tracks = tracks
            self._recent_tracks_loaded = True
        return tracks

    def load_playlists(self, *, limit: int = 20, refresh: bool = False) -> tuple[SpotifyPlaylist, ...]:
        """Return user playlists, using warmed data when possible."""
        with self._library_lock:
            if self._playlists_loaded and not refresh and len(self._playlists) >= min(limit, self.LIBRARY_WARM_LIMIT):
                return self._playlists[:limit]
        playlists = self._controller.playlists(limit=limit)
        with self._library_lock:
            self._playlists = playlists
            self._playlists_loaded = True
        return playlists

    def load_playlist_tracks(self, playlist_id: str, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        """Load tracks for one Spotify playlist on a worker thread."""
        return self._controller.playlist_tracks(playlist_id, limit=limit)

    def _warm_library(self) -> None:
        """Warm common Spotify browse data while the user enters ORC UI."""
        if self._stop.wait(0.75):
            return
        loaders = (self.load_recently_played, self.load_saved_tracks, self.load_playlists)
        for loader in loaders:
            if self._stop.is_set():
                return
            try:
                loader(limit=self.LIBRARY_WARM_LIMIT)
            except Exception as error:
                print(f"WARNING: Spotify library warm failed: {type(error).__name__}: {error}")

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
            print(f"WARNING: Spotify state refresh failed: {type(error).__name__}: {error}")
            return
        with self._state_lock:
            self._state = state
