# SPDX-License-Identifier: MIT

"""Controller-owned library queries, destination selection, and card artwork."""

from collections.abc import Callable
from dataclasses import replace

from controllers.spotify.spotify_local_player import SpotifyLocalPlayer
from controllers.spotify.spotify_state_service import SpotifyStateService
from ui.media.spotify_browse_if import (
    SpotifyBrowseState, SpotifyBrowseUi, SpotifyCollection, SpotifyPlaybackMode,
)
from ui.ui_dispatcher_if import UiDispatcherIf

LIMIT = 18


class SpotifyBrowser:
    def __init__(self, service: SpotifyStateService, player: SpotifyLocalPlayer | None, *,
                 run_work: Callable[[Callable[[], None]], None], dispatcher: UiDispatcherIf,
                 load_artwork: Callable[[str], bytes], online: Callable[[], bool],
                 show_now_playing: Callable[[], None]) -> None:
        self._service = service
        self._player = player
        self._run_work = run_work
        self._dispatcher = dispatcher
        self._load_artwork = load_artwork
        self._online = online
        self._show_now_playing = show_now_playing
        self._view: SpotifyBrowseUi | None = None
        self._state = SpotifyBrowseState()
        self._generation = 0
        self._collection_generation = 0
        self._timer: object | None = None
        self._closed = False
        self._was_online = online()

    def activate(self, view: SpotifyBrowseUi) -> None:
        if self._closed:
            raise RuntimeError("Spotify browser is closed")
        self.deactivate()
        self._view = view
        view.set_browse_request_handler(self)
        self._state = SpotifyBrowseState()
        self._was_online = True
        self._tick()

    def deactivate(self) -> None:
        self._generation += 1
        self._collection_generation += 1
        if self._timer is not None:
            self._dispatcher.cancel_ui_callback(self._timer)
            self._timer = None
        view, self._view = self._view, None
        if view is not None:
            view.set_browse_request_handler(None)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.deactivate()
        self._state = SpotifyBrowseState()

    def _tick(self) -> None:
        self._timer = None
        if self._closed or self._view is None:
            return
        online = self._online()
        if not online and self._was_online:
            self._collection_generation += 1
            self._state = replace(self._state, tracks=(), playlists=(), loading=False,
                                  message="Offline mode: Spotify unavailable")
        self._was_online = online
        if self._player is not None:
            self._state = replace(self._state, player=self._player.state())
        self._publish()
        self._timer = self._dispatcher.schedule_ui_callback(200, self._tick)

    def _publish(self) -> None:
        if self._view is not None and not self._closed:
            self._view.set_browse_state(self._state)

    def _work(self, work: Callable[[], Callable[[], None]]) -> None:
        generation, collection = self._generation, self._collection_generation
        def current() -> bool:
            return (not self._closed and self._view is not None and self._online()
                    and generation == self._generation and collection == self._collection_generation)
        def run() -> None:
            if not current():
                return
            finish = work()
            def deliver() -> None:
                if current():
                    finish()
            self._dispatcher.dispatch_ui(deliver)
        self._run_work(run)

    def request_collection(self, collection: SpotifyCollection) -> None:
        if self._closed or self._view is None or not self._online():
            return
        if collection is SpotifyCollection.PLAYLIST:
            return
        self._collection_generation += 1
        titles = {SpotifyCollection.LIKED: "LIKED SONGS", SpotifyCollection.RECENT: "RECENTLY PLAYED",
                  SpotifyCollection.PLAYLISTS: "PLAYLISTS"}
        self._state = replace(self._state, collection=collection, title=titles.get(collection, ""),
                              tracks=(), playlists=(), loading=False, message="")
        if collection in (SpotifyCollection.NOW, SpotifyCollection.HOME):
            self._publish()
            return
        if collection is SpotifyCollection.PLAYLISTS:
            cached = self._service.cached_playlists()
            if cached is not None:
                self._state = replace(self._state, playlists=cached[:LIMIT])
                self._finish_collection()
                return
        else:
            cached_tracks = (self._service.cached_saved_tracks() if collection is SpotifyCollection.LIKED
                             else self._service.cached_recently_played())
            if cached_tracks is not None:
                self._state = replace(self._state, tracks=cached_tracks[:LIMIT])
                self._finish_collection()
                return
        self._state = replace(self._state, loading=True)
        self._publish()
        def load() -> Callable[[], None]:
            try:
                if collection is SpotifyCollection.PLAYLISTS:
                    playlists = self._service.load_playlists(limit=LIMIT)
                    def finish() -> None:
                        self._state = replace(self._state, playlists=playlists)
                        self._finish_collection()
                else:
                    tracks = (self._service.load_saved_tracks(limit=LIMIT) if collection is SpotifyCollection.LIKED
                              else self._service.load_recently_played(limit=LIMIT))
                    def finish() -> None:
                        self._state = replace(self._state, tracks=tracks)
                        self._finish_collection()
                return finish
            except Exception as error:
                return self._error(str(error))
        self._work(load)

    def _error(self, message: str) -> Callable[[], None]:
        def finish() -> None:
            self._state = replace(self._state, loading=False, message=f"Spotify: {message}")
            self._publish()
        return finish

    def _finish_collection(self) -> None:
        self._state = replace(self._state, loading=False)
        self._publish()
        urls = {track.album_art_url for track in self._state.tracks}
        urls.update(playlist.image_url for playlist in self._state.playlists)
        for uri in urls:
            if uri:
                self._request_artwork(uri)

    def _request_artwork(self, uri: str) -> None:
        def load() -> Callable[[], None]:
            try:
                payload = self._load_artwork(uri)
            except Exception:
                payload = None
            def finish() -> None:
                if self._view is not None:
                    self._view.set_browse_artwork(uri, payload)
            return finish
        self._work(load)

    def request_playlist(self, playlist_id: str) -> None:
        if self._closed or self._view is None or not self._online():
            return
        playlist = next((item for item in self._state.playlists if item.playlist_id == playlist_id), None)
        if playlist is None:
            return
        self._collection_generation += 1
        self._state = replace(self._state, collection=SpotifyCollection.PLAYLIST,
                              title=playlist.name.upper(), playlists=(), tracks=(), loading=True, message="")
        self._publish()
        def load() -> Callable[[], None]:
            try:
                tracks = self._service.load_playlist_tracks(playlist_id, limit=LIMIT)
            except Exception as error:
                return self._error(str(error))
            def finish() -> None:
                self._state = replace(self._state, tracks=tracks)
                self._finish_collection()
            return finish
        self._work(load)

    def request_play_track(self, uri: str) -> None:
        if self._closed or self._view is None or not self._online():
            return
        if not any(track.uri == uri for track in self._state.tracks):
            return
        self._service.request_play_track(uri)
        self._service.request_refresh()
        self._show_now_playing()

    def request_playback_mode(self, mode: SpotifyPlaybackMode) -> None:
        if self._closed or self._view is None or not self._online() or self._player is None:
            return
        state = self._player.state()
        if state.busy or (mode is SpotifyPlaybackMode.PLAYER and not state.available):
            return
        if mode is SpotifyPlaybackMode.PLAYER:
            self._player.request_player()
        else:
            self._player.request_remote()
        self._service.request_refresh()
        self._state = replace(self._state, player=self._player.state())
        self._publish()
