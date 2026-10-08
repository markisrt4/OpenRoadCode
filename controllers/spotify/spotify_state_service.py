# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Background Spotify state/control service independent of concrete UI toolkits."""

from __future__ import annotations

import queue
import logging
import threading
import time
from collections.abc import Callable

from common.logging.structured import current_operation, event, operation

from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from ui.media.spotify_library import (SpotifyLibraryTrack, SpotifyPlaylist)
from controllers.spotify.spotify_media_presenter import SpotifyMediaPresenter
from controllers.spotify.spotify_state import SpotifyState
from protocols.spotify.spotify_web_api_client import SpotifyWebApiError
from ui.media import (
    MediaState,
    MediaUiStub,
    PlaybackRequestHandlerIf,
    SeekRequestHandlerIf,
    TrackRequestHandlerIf,
    VolumeRequestHandlerIf,
)

LOGGER = logging.getLogger("media.spotify")
LIBRARY_LOGGER = logging.getLogger("media.library")


class _SynchronizedSpotifyController(SpotifyControllerIf):
    """Serialize access to one Spotify controller across worker threads."""

    def __init__(self, backend: SpotifyControllerIf) -> None:
        self._backend = backend
        self.network_allowed: Callable[[], bool] = lambda: True
        self._lock = threading.RLock()

    def current_state(self) -> SpotifyState:
        with self._lock:
            if not self.network_allowed():
                raise RuntimeError("Spotify unavailable in offline mode")
            return self._backend.current_state()

    def play(self) -> None:
        with self._lock:
            if not self.network_allowed():
                raise RuntimeError("Spotify unavailable in offline mode")
            self._backend.play()

    def pause(self) -> None:
        with self._lock:
            if not self.network_allowed():
                raise RuntimeError("Spotify unavailable in offline mode")
            self._backend.pause()

    def play_pause(self) -> None:
        with self._lock:
            if not self.network_allowed():
                raise RuntimeError("Spotify unavailable in offline mode")
            self._backend.play_pause()

    def next_track(self) -> None:
        with self._lock:
            if not self.network_allowed():
                raise RuntimeError("Spotify unavailable in offline mode")
            self._backend.next_track()

    def previous_track(self) -> None:
        with self._lock:
            if not self.network_allowed():
                raise RuntimeError("Spotify unavailable in offline mode")
            self._backend.previous_track()

    def set_volume_percent(self, volume_percent: int) -> None:
        with self._lock:
            if not self.network_allowed():
                raise RuntimeError("Spotify unavailable in offline mode")
            self._backend.set_volume_percent(volume_percent)

    def seek_to_position_ms(self, position_ms: int) -> None:
        with self._lock:
            if not self.network_allowed():
                raise RuntimeError("Spotify unavailable in offline mode")
            self._backend.seek_to_position_ms(position_ms)

    def transfer_playback(self, device_id: str, *, play: bool = True) -> None:
        with self._lock:
            if not self.network_allowed():
                raise RuntimeError("Spotify unavailable in offline mode")
            self._backend.transfer_playback(device_id, play=play)

    def saved_tracks(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        with self._lock:
            if not self.network_allowed():
                raise RuntimeError("Spotify unavailable in offline mode")
            return self._backend.saved_tracks(limit=limit)

    def recently_played(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        with self._lock:
            if not self.network_allowed():
                raise RuntimeError("Spotify unavailable in offline mode")
            return self._backend.recently_played(limit=limit)

    def playlists(self, *, limit: int = 20) -> tuple[SpotifyPlaylist, ...]:
        with self._lock:
            if not self.network_allowed():
                raise RuntimeError("Spotify unavailable in offline mode")
            return self._backend.playlists(limit=limit)

    def playlist_tracks(
        self,
        playlist_id: str,
        *,
        limit: int = 20,
    ) -> tuple[SpotifyLibraryTrack, ...]:
        with self._lock:
            if not self.network_allowed():
                raise RuntimeError("Spotify unavailable in offline mode")
            return self._backend.playlist_tracks(playlist_id, limit=limit)

    def play_track(self, track_uri: str) -> None:
        with self._lock:
            if not self.network_allowed():
                raise RuntimeError("Spotify unavailable in offline mode")
            self._backend.play_track(track_uri)


class SpotifyStateService(
    PlaybackRequestHandlerIf,
    TrackRequestHandlerIf,
    SeekRequestHandlerIf,
    VolumeRequestHandlerIf,
):
    """Cache Spotify playback/library state and keep API work off the UI thread."""

    DEFAULT_REFRESH_SECONDS = 5.0
    MIN_REFRESH_SECONDS = 5.0
    DEFAULT_RATE_LIMIT_SECONDS = 30.0

    def __init__(
        self,
        controller: SpotifyControllerIf,
        *,
        refresh_seconds: float = DEFAULT_REFRESH_SECONDS,
    ) -> None:
        if refresh_seconds < self.MIN_REFRESH_SECONDS:
            raise ValueError(
                f"refresh_seconds must be at least {self.MIN_REFRESH_SECONDS} seconds"
            )
        self._network_allowed: Callable[[], bool] = lambda: True
        self._controller = _SynchronizedSpotifyController(controller)
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
        self._last_refresh_at = 0.0
        self._backoff_until = 0.0
        self._observed_state: MediaState | None = None
        self._observed_track_uri: str | None = None

    def set_network_allowed(self, allowed: Callable[[], bool]) -> None:
        self._network_allowed = allowed
        self._controller.network_allowed = allowed
        self._wake.set()

    @property
    def controller(self) -> SpotifyControllerIf:
        """Return the synchronized backend for worker-only integrations."""
        return self._controller

    def start(self) -> None:
        """Start the playback state worker."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="spotify-state-service",
            daemon=True,
        )
        self._thread.start()
        event(LOGGER, logging.INFO, "worker.started", "Spotify state worker started")

    def close(self) -> None:
        """Stop the background Spotify worker."""
        self._stop.set()
        self._wake.set()
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)
        if thread is not None:
            event(
                LOGGER,
                logging.WARNING if thread.is_alive() else logging.INFO,
                "worker.stop_pending" if thread.is_alive() else "worker.stopped",
                "Spotify state worker stop requested"
                if thread.is_alive()
                else "Spotify state worker stopped",
            )

    def latest_state(self) -> MediaState:
        """Return the latest cached Spotify media state."""
        with self._state_lock:
            return self._state

    def request_refresh(self) -> None:
        """Request a refresh subject to rate limiting and request coalescing."""
        self._wake.set()

    def request_play(self) -> None:
        self._enqueue(self._controller.play, "play")

    def request_pause(self) -> None:
        self._enqueue(self._controller.pause, "pause")

    def request_previous_track(self) -> None:
        self._enqueue(self._controller.previous_track, "previous_track")

    def request_next_track(self) -> None:
        self._enqueue(self._controller.next_track, "next_track")

    def request_rewind(self, seconds: float) -> None:
        state = self.latest_state()
        self.request_seek(max(0.0, (state.position_s or 0.0) - seconds))

    def request_forward(self, seconds: float) -> None:
        state = self.latest_state()
        self.request_seek((state.position_s or 0.0) + seconds)

    def request_seek(self, position_s: float) -> None:
        position_ms = int(max(0.0, position_s) * 1000.0)
        self._enqueue(lambda: self._controller.seek_to_position_ms(position_ms), "seek")

    def request_volume(self, volume_percent: int) -> None:
        clamped = max(0, min(100, volume_percent))
        self._enqueue(lambda: self._controller.set_volume_percent(clamped), "volume")

    def request_transfer_playback(self, device_id: str, *, play: bool = True) -> None:
        self._enqueue(lambda: self._controller.transfer_playback(device_id, play=play), "transfer")

    def request_play_track(self, track_uri: str) -> None:
        self._enqueue(lambda: self._controller.play_track(track_uri), "play_track")

    def cached_saved_tracks(self) -> tuple[SpotifyLibraryTrack, ...] | None:
        with self._library_lock:
            return self._saved_tracks if self._saved_tracks_loaded else None

    def cached_recently_played(self) -> tuple[SpotifyLibraryTrack, ...] | None:
        with self._library_lock:
            return self._recent_tracks if self._recent_tracks_loaded else None

    def cached_playlists(self) -> tuple[SpotifyPlaylist, ...] | None:
        with self._library_lock:
            return self._playlists if self._playlists_loaded else None

    def load_saved_tracks(
        self,
        *,
        limit: int = 20,
        refresh: bool = False,
    ) -> tuple[SpotifyLibraryTrack, ...]:
        with self._library_lock:
            if self._saved_tracks_loaded and not refresh:
                return self._saved_tracks[:limit]
        tracks = self._load_library(
            "saved_tracks", lambda: self._controller.saved_tracks(limit=limit)
        )
        with self._library_lock:
            self._saved_tracks = tracks
            self._saved_tracks_loaded = True
        return tracks

    def load_recently_played(
        self,
        *,
        limit: int = 20,
        refresh: bool = False,
    ) -> tuple[SpotifyLibraryTrack, ...]:
        with self._library_lock:
            if self._recent_tracks_loaded and not refresh:
                return self._recent_tracks[:limit]
        tracks = self._load_library(
            "recently_played", lambda: self._controller.recently_played(limit=limit)
        )
        with self._library_lock:
            self._recent_tracks = tracks
            self._recent_tracks_loaded = True
        return tracks

    def load_playlists(
        self,
        *,
        limit: int = 20,
        refresh: bool = False,
    ) -> tuple[SpotifyPlaylist, ...]:
        with self._library_lock:
            if self._playlists_loaded and not refresh:
                return self._playlists[:limit]
        playlists = self._load_library("playlists", lambda: self._controller.playlists(limit=limit))
        with self._library_lock:
            self._playlists = playlists
            self._playlists_loaded = True
        return playlists

    def load_playlist_tracks(
        self,
        playlist_id: str,
        *,
        limit: int = 20,
    ) -> tuple[SpotifyLibraryTrack, ...]:
        return self._load_library(
            "playlist_tracks", lambda: self._controller.playlist_tracks(playlist_id, limit=limit)
        )

    def _load_library(self, collection: str, loader: Callable):
        with operation(current_operation()):
            event(
                LIBRARY_LOGGER,
                logging.INFO,
                "library.load_started",
                "Media library load started",
                collection=collection,
            )
            try:
                result = loader()
            except Exception as error:
                event(
                    LIBRARY_LOGGER,
                    logging.ERROR,
                    "library.load_failed",
                    "Media library load failed",
                    collection=collection,
                    exception_type=type(error).__name__,
                    http_status=error.status_code
                    if isinstance(error, SpotifyWebApiError)
                    else None,
                )
                raise
            event(
                LIBRARY_LOGGER,
                logging.INFO,
                "library.load_completed",
                "Media library load completed",
                collection=collection,
                item_count=len(result),
            )
            return result

    def _enqueue(self, command: Callable[[], None], action: str) -> None:
        if not self._network_allowed():
            return
        level = logging.DEBUG if action in {"volume", "seek"} else logging.INFO
        with operation(current_operation()) as operation_id:
            event(LOGGER, level, "command.queued", "Spotify command queued", action=action)

        def execute() -> None:
            with operation(operation_id):
                try:
                    command()
                except Exception as error:
                    event(
                        LOGGER,
                        logging.ERROR,
                        "command.failed",
                        "Spotify command failed",
                        action=action,
                        exception_type=type(error).__name__,
                        http_status=error.status_code
                        if isinstance(error, SpotifyWebApiError)
                        else None,
                    )
                    if isinstance(error, SpotifyWebApiError):
                        self._handle_rate_limit(error, context="command")
                    raise
                event(
                    LOGGER, level, "command.completed", "Spotify command completed", action=action
                )

        self._commands.put(execute)
        self._wake.set()

    def _run(self) -> None:
        try:
            self._poll()
        except Exception as error:
            event(
                LOGGER,
                logging.ERROR,
                "worker.failed",
                "Spotify state worker failed",
                exception_type=type(error).__name__,
            )
            raise
        finally:
            event(LOGGER, logging.INFO, "worker.exited", "Spotify state worker exited")

    def _poll(self) -> None:
        while not self._stop.is_set():
            command_ran = self._drain_commands()
            if not self._network_allowed():
                self._wake.wait(1.0)
                self._wake.clear()
                continue
            now = time.monotonic()
            earliest_refresh = max(
                self._last_refresh_at + self._refresh_seconds,
                self._backoff_until,
            )
            if self._last_refresh_at == 0.0 or now >= earliest_refresh:
                self._refresh_state()
                continue
            wait_seconds = max(0.05, earliest_refresh - now)
            if command_ran:
                wait_seconds = min(wait_seconds, self._refresh_seconds)
            self._wake.wait(wait_seconds)
            self._wake.clear()

    def _drain_commands(self) -> bool:
        command_ran = False
        while not self._stop.is_set():
            try:
                command = self._commands.get_nowait()
            except queue.Empty:
                return command_ran
            if not self._network_allowed():
                continue
            command_ran = True
            try:
                command()
            except Exception:
                # The queued operation records its safe failure context.
                pass
        return command_ran

    def _refresh_state(self) -> None:
        if not self._network_allowed():
            return
        self._last_refresh_at = time.monotonic()
        try:
            state = self._presenter.read_state()
        except SpotifyWebApiError as error:
            self._handle_rate_limit(error, context="state refresh")
            return
        except Exception as error:
            event(
                LOGGER,
                logging.WARNING,
                "state.refresh_failed",
                "Spotify state refresh failed",
                exception_type=type(error).__name__,
            )
            return
        with self._state_lock:
            self._state = state
        previous = self._observed_state
        if previous is None or previous.availability != state.availability:
            event(
                LOGGER,
                logging.INFO,
                "state.availability_changed",
                "Spotify availability changed",
                availability=state.availability.name,
            )
        if previous is None or previous.playback != state.playback:
            event(
                LOGGER,
                logging.INFO,
                "state.playback_changed",
                "Spotify playback state changed",
                playback=state.playback.name,
            )
        if state.media_uri and self._observed_track_uri != state.media_uri:
            event(LOGGER, logging.INFO, "state.track_changed", "Spotify track changed")
            self._observed_track_uri = state.media_uri
        self._observed_state = state
        event(LOGGER, logging.DEBUG, "state.refreshed", "Spotify playback state refreshed")

    def _handle_rate_limit(self, error: SpotifyWebApiError, *, context: str) -> None:
        if error.status_code != 429:
            if context != "command":
                event(
                    LOGGER,
                    logging.WARNING,
                    "state.refresh_failed",
                    "Spotify state refresh failed",
                    exception_type=type(error).__name__,
                    http_status=error.status_code,
                )
            return
        retry_after = error.retry_after_seconds or self.DEFAULT_RATE_LIMIT_SECONDS
        self._backoff_until = max(
            self._backoff_until,
            time.monotonic() + retry_after,
        )
        event(
            LOGGER,
            logging.WARNING,
            "api.rate_limited",
            "Spotify API rate limited",
            context=context,
            http_status=429,
            retry_after_s=retry_after,
        )
