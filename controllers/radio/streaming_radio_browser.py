# SPDX-License-Identifier: MIT

"""Controller-owned directory, favorite, playback, and artwork browser work."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
import threading

from ui.radio.streaming_radio_session_if import StreamingRadioRequestHandlerIf, StreamingRadioUiIf
from ui.radio.streaming_radio_state import StreamingRadioBrowseMode, StreamingRadioBrowserState
from ui.radio.streaming_radio_types import StreamingRadioStation

from .streaming_radio_backend_if import StreamingRadioBackendIf, StreamingRadioFavoritesIf
from .streaming_radio_directory_if import StreamingRadioDirectoryIf

WorkScheduler = Callable[[Callable[[], None]], None]
ArtworkLoader = Callable[[str], bytes]


class StreamingRadioBrowser(StreamingRadioRequestHandlerIf):
    """Own one presentation session while playback remains application-owned."""

    def __init__(
        self, directory: StreamingRadioDirectoryIf, playback: StreamingRadioBackendIf,
        favorites: StreamingRadioFavoritesIf, *, run_work: WorkScheduler,
        run_ui: WorkScheduler, load_artwork: ArtworkLoader,
        on_close: Callable[[], None] = lambda: None,
        run_artwork: WorkScheduler | None = None,
    ) -> None:
        self._directory = directory
        self._playback = playback
        self._favorites = favorites
        self._run_work = run_work
        self._run_artwork = run_artwork if run_artwork is not None else run_work
        self._run_ui = run_ui
        self._load_artwork = load_artwork
        self._on_close = on_close
        self._view: StreamingRadioUiIf | None = None
        self._state = StreamingRadioBrowserState(favorite_station_ids=favorites.station_ids)
        self._generation = 0
        self._load_generation = 0
        self._closed = False
        self._playback_busy = False
        self._playback_generation = 0
        self._artwork: dict[str, tuple[str, bytes]] = {}
        self._artwork_requested: set[tuple[str, str]] = set()
        self._favorite_busy: set[str] = set()
        self._favorite_lock = threading.Lock()

    def activate(self, view: StreamingRadioUiIf) -> None:
        """Bind the frontend and refresh the retained browsing mode."""
        if self._closed:
            raise RuntimeError("Streaming radio session is closed")
        self.deactivate()
        self._view = view
        view.set_streaming_request_handler(self)
        self._state = replace(
            self._state, playback_busy=self._playback_busy,
            favorite_station_ids=self._favorites.station_ids,
            playback=self._playback.snapshot(),
        )
        self.request_mode(self._state.mode)

    def deactivate(self) -> None:
        """Retire deliveries without stopping application-owned audio playback."""
        self._generation += 1
        self._load_generation += 1
        self._artwork_requested.clear()
        self._favorite_busy.clear()
        self._playback_generation += 1
        self._playback_busy = False
        view, self._view = self._view, None
        if view is not None:
            view.set_streaming_request_handler(None)

    def close(self) -> None:
        """Permanently retire this browser, including callbacks already queued."""
        if self._closed:
            return
        self._closed = True
        try:
            self.deactivate()
        finally:
            self._artwork.clear()
            self._state = StreamingRadioBrowserState()
            self._on_close()

    def _dispatch(self, generation: int, callback: Callable[[], None]) -> None:
        def deliver() -> None:
            if not self._closed and generation == self._generation and self._view is not None:
                callback()
        self._run_ui(deliver)

    def _publish(self) -> None:
        view = self._view
        if view is not None and not self._closed:
            self._state = replace(
                self._state, playback=self._playback.snapshot(),
                favorite_station_ids=self._favorites.station_ids,
                playback_busy=self._playback_busy,
            )
            view.set_streaming_state(self._state)

    def request_mode(self, mode: StreamingRadioBrowseMode) -> None:
        """Load a mode asynchronously; superseded directory results are discarded."""
        if self._closed or self._view is None:
            return
        mode = StreamingRadioBrowseMode(mode)
        self._load_generation += 1
        load_generation, generation = self._load_generation, self._generation
        station_ids = self._favorites.ordered_station_ids
        self._state = replace(self._state, mode=mode, loading=True, error=False, message="")
        self._publish()
        def load() -> None:
            if self._closed or generation != self._generation:
                return
            stations: tuple[StreamingRadioStation, ...] = ()
            message = ""
            try:
                if mode is StreamingRadioBrowseMode.FAVORITES:
                    stations = self._directory.stations_by_ids(station_ids) if station_ids else ()
                elif mode is StreamingRadioBrowseMode.LOCAL:
                    stations = self._directory.stations_near(
                        latitude=42.3314, longitude=-83.0458, radius_km=80.0,
                        state="Michigan", country_code="US", limit=50,
                    )
                else:
                    stations = self._directory.stations_by_region(
                        state="Michigan", country_code="US", limit=100,
                    )
            except Exception as error:
                message = f"Unable to load stations: {type(error).__name__}: {error}"
            self._dispatch(generation, lambda: self._finish_load(load_generation, stations, message))
        self._run_work(load)

    def _finish_load(
        self, generation: int, stations: tuple[StreamingRadioStation, ...], message: str,
    ) -> None:
        if generation != self._load_generation:
            return
        self._state = replace(self._state, stations=stations, loading=False, message=message, error=bool(message))
        self._publish()

    def _station(self, station_id: str) -> StreamingRadioStation | None:
        return next((s for s in self._state.stations if s.station_id == station_id), None)

    def request_play(self, station_id: str) -> None:
        station = self._station(station_id)
        if station is not None:
            self._request_playback(station)

    def request_stop(self) -> None:
        self._request_playback(None)

    def _request_playback(self, station: StreamingRadioStation | None) -> None:
        if self._closed or self._view is None or self._playback_busy:
            return
        generation = self._generation
        self._playback_generation += 1
        playback_generation = self._playback_generation
        self._playback_busy = True
        message = f"Connecting to {station.name}…" if station is not None else "Stopping stream…"
        self._state = replace(self._state, message=message, error=False)
        self._publish()
        def playback() -> None:
            message = ""
            try:
                # A request that has not begun when the view retires has no effect.
                # Already running playback belongs to the application and continues.
                if not self._closed and generation == self._generation:
                    self._playback.stop() if station is None else self._playback.play(station)
            except Exception as error:
                message = f"Playback failed: {type(error).__name__}: {error}"
            finally:
                self._run_ui(lambda: self._finish_playback(generation, playback_generation, message))
        self._run_work(playback)

    def _finish_playback(self, generation: int, playback_generation: int, message: str) -> None:
        if playback_generation != self._playback_generation:
            return
        self._playback_busy = False
        if self._closed or generation != self._generation or self._view is None:
            return
        self._state = replace(self._state, message=message, error=bool(message))
        self._publish()

    def request_toggle_favorite(self, station_id: str) -> None:
        if self._closed or self._view is None or station_id in self._favorite_busy or self._station(station_id) is None:
            return
        self._favorite_busy.add(station_id)
        generation = self._generation
        def toggle() -> None:
            message = ""
            try:
                with self._favorite_lock:
                    if not self._closed and generation == self._generation:
                        self._favorites.toggle(station_id)
            except (OSError, ValueError) as error:
                message = f"Unable to save favorite: {error}"
            self._run_ui(lambda: self._finish_favorite(generation, station_id, message))
        self._run_work(toggle)

    def _finish_favorite(self, generation: int, station_id: str, message: str) -> None:
        if self._closed or generation != self._generation or self._view is None:
            return
        self._favorite_busy.discard(station_id)
        self._state = replace(self._state, message=message, error=bool(message))
        if not message and self._state.mode is StreamingRadioBrowseMode.FAVORITES:
            self.request_mode(self._state.mode)
        else:
            self._publish()

    def request_artwork(self, station_id: str) -> None:
        station = self._station(station_id)
        if self._closed or self._view is None or station is None or not station.artwork_url:
            return
        url = station.artwork_url
        cached = self._artwork.get(station_id)
        if cached is not None and cached[0] == url:
            self._view.set_station_artwork(station_id, cached[1])
            return
        key = (station_id, url)
        if key in self._artwork_requested:
            return
        self._artwork_requested.add(key)
        generation = self._generation
        def artwork() -> None:
            if self._closed or generation != self._generation:
                return
            payload: bytes | None = None
            try:
                payload = self._load_artwork(url)
            except Exception:
                pass  # Missing/broken artwork retains the frontend placeholder.
            self._dispatch(generation, lambda: self._finish_artwork(station_id, url, payload))
        self._run_artwork(artwork)

    def _finish_artwork(self, station_id: str, url: str, payload: bytes | None) -> None:
        current = self._station(station_id)
        if payload is None or current is None or current.artwork_url != url:
            return
        self._artwork[station_id] = (url, payload)
        view = self._view
        if view is not None:
            view.set_station_artwork(station_id, payload)
