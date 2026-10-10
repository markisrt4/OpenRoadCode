# SPDX-License-Identifier: MIT

"""Controller-owned artwork, lyrics, video work and presentation lifetime."""

from collections.abc import Callable
from dataclasses import replace
import time

from controllers.lyrics.lrclib_lyrics_client import LyricsResult
from ui.media import MediaAvailability, MediaState, PlaybackRequestHandlerIf, TrackRequestHandlerIf, SeekRequestHandlerIf
from ui.media.spotify_presentation_if import (
    SpotifyPresentationState, SpotifyPresentationUi, SpotifyRequestHandler,
)
from ui.ui_dispatcher_if import UiDispatcherIf


class SpotifyPresentation(SpotifyRequestHandler):
    """One visible view; all completions are guarded by view and track generations."""

    def __init__(
        self, *, read_state: Callable[[], MediaState], online: Callable[[], bool],
        load_artwork: Callable[[str], bytes],
        load_lyrics: Callable[[MediaState], LyricsResult | None],
        video_available: Callable[[], bool], video_active: Callable[[], bool],
        watch_video: Callable[[Callable[[], bool], Callable[[], bool]], bool],
        return_to_spotify: Callable[[Callable[[], bool]], None],
        run_work: Callable[[Callable[[], None]], None], dispatcher: UiDispatcherIf,
        read_video_process_id: Callable[[], int | None] = lambda: None,
        playback: PlaybackRequestHandlerIf | None = None,
        tracks: TrackRequestHandlerIf | None = None, seek: SeekRequestHandlerIf | None = None,
        rich: bool = True, set_volume: Callable[[int], None] = lambda _volume: None,
    ) -> None:
        self._playback = playback
        self._tracks = tracks
        self._seek = seek
        self._read_state = read_state
        self._online = online
        self._load_artwork = load_artwork
        self._load_lyrics = load_lyrics
        self._video_available = video_available
        self._video_active = video_active
        self._watch_video = watch_video
        self._return = return_to_spotify
        self._run_work = run_work
        self._dispatcher = dispatcher
        self._read_video_process_id = read_video_process_id
        self._rich = rich
        self._set_volume = set_volume
        self._pending_volume: int | None = None
        self._volume_until = 0.0
        self._returning_video = False
        self._view: SpotifyPresentationUi | None = None
        self._state = SpotifyPresentationState()
        self._generation = 0
        self._track_generation = 0
        self._key: tuple[object, ...] | None = None
        self._lyrics: LyricsResult | None = None
        self._timer: object | None = None
        self._closed = False

    def activate(self, view: SpotifyPresentationUi) -> None:
        if self._closed:
            raise RuntimeError("Spotify presentation is closed")
        self.deactivate()
        self._view = view
        view.set_spotify_request_handler(self if self._rich else None)
        view.set_video_request_handler(self if self._rich else None)
        self._tick()

    def deactivate(self) -> None:
        self._generation += 1
        self._track_generation += 1
        if self._timer is not None:
            self._dispatcher.cancel_ui_callback(self._timer)
            self._timer = None
        view, self._view = self._view, None
        if view is not None:
            view.set_spotify_request_handler(None)
            view.set_video_request_handler(None)
        self._key = None
        self._returning_video = False
        self._pending_volume = None
        self._lyrics = None
        self._state = SpotifyPresentationState()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.deactivate()

    def _publish(self) -> None:
        if self._view is not None and not self._closed:
            self._view.set_spotify_state(self._state)

    def _tick(self) -> None:
        self._timer = None
        if self._closed or self._view is None:
            return
        online = self._online()
        media = self._read_state() if online else MediaState()
        if self._pending_volume is not None:
            if media.volume_percent == self._pending_volume or time.monotonic() >= self._volume_until:
                self._pending_volume = None
            else:
                media = replace(media, volume_percent=self._pending_volume)
        valid = online and media.availability is MediaAvailability.AVAILABLE
        key = (media.media_uri, media.title, media.artist, media.album, media.duration_s,
               media.artwork_uri, valid)
        self._state = replace(self._state, media=media, online=online,
                              video_active=self._video_active() if online and self._rich and not self._returning_video else False,
                              video_process_id=self._read_video_process_id() if online and self._rich else None)
        if key != self._key:
            self._key = key
            self._track_generation += 1
            self._lyrics = None
            self._returning_video = False
            self._state = replace(self._state, artwork=None, artwork_loading=False,
                                  lyric_current="", lyric_next="", video_available=False,
                                  video_busy=False, message="")
            if valid:
                self._start_track(media)
        self._render_lyrics()
        self._publish()
        self._timer = self._dispatcher.schedule_ui_callback(500, self._tick)

    def _work(self, work: Callable[[], Callable[[], None]]) -> None:
        generation, track = self._generation, self._track_generation
        def current() -> bool:
            return (not self._closed and self._view is not None
                    and generation == self._generation and track == self._track_generation
                    and self._online())
        def run() -> None:
            if not current():
                return
            finish = work()
            def deliver() -> None:
                if current():
                    finish()
                    self._publish()
            self._dispatcher.dispatch_ui(deliver)
        self._run_work(run)

    def _start_track(self, media: MediaState) -> None:
        if media.artwork_uri:
            self._state = replace(self._state, artwork_loading=True)
            uri = media.artwork_uri
            def artwork() -> Callable[[], None]:
                try:
                    payload = self._load_artwork(uri)
                except Exception:
                    payload = None
                def finish() -> None:
                    self._state = replace(self._state, artwork=payload, artwork_loading=False)
                return finish
            self._work(artwork)
        if not self._rich or not media.title or not media.artist:
            return
        self._state = replace(self._state, lyric_current="Finding lyrics…", video_available=None)
        def lyrics() -> Callable[[], None]:
            try:
                result = self._load_lyrics(media)
            except Exception:
                result = None
            def finish() -> None:
                self._lyrics = result
                self._state = replace(self._state, lyric_current="Lyrics unavailable")
                self._render_lyrics()
            return finish
        self._work(lyrics)
        def video() -> Callable[[], None]:
            try:
                available = self._video_available()
            except Exception:
                available = False
            def finish() -> None:
                self._state = replace(self._state, video_available=available)
            return finish
        self._work(video)

    def _render_lyrics(self) -> None:
        result = self._lyrics
        if result is None:
            return
        media = self._state.media
        if result.synced_lines:
            position_ms = (media.position_s or 0.0) * 1000
            index = 0
            for number, line in enumerate(result.synced_lines):
                if line.time_ms > position_ms:
                    break
                index = number
            lines = tuple(line.text for line in result.synced_lines)
        else:
            lines = result.plain_lines
            ratio = min(1.0, max(0.0, (media.position_s or 0.0) / media.duration_s)) if media.duration_s else 0.0
            index = min(len(lines) - 1, int(ratio * len(lines)))
        current = lines[index] if lines else "Lyrics unavailable"
        following = lines[index + 1] if lines and index + 1 < len(lines) else ""
        self._state = replace(self._state, lyric_current=current, lyric_next=following)

    def _request(self, action: Callable[[], None]) -> None:
        if self._closed or self._view is None or not self._online():
            return
        action()

    def request_play(self) -> None:
        if self._playback is not None:
            self._request(self._playback.request_play)

    def request_pause(self) -> None:
        if self._playback is not None:
            self._request(self._playback.request_pause)

    def request_previous_track(self) -> None:
        if self._tracks is not None:
            self._request(self._tracks.request_previous_track)

    def request_next_track(self) -> None:
        if self._tracks is not None:
            self._request(self._tracks.request_next_track)

    def request_seek(self, position_s: float) -> None:
        handler = self._seek
        if handler is not None:
            self._request(lambda: handler.request_seek(position_s))

    def request_rewind(self, seconds: float) -> None:
        self.request_seek(max(0.0, (self._state.media.position_s or 0.0) - seconds))

    def request_forward(self, seconds: float) -> None:
        self.request_seek((self._state.media.position_s or 0.0) + seconds)

    def request_volume(self, volume_percent: int) -> None:
        """Render latest volume intent while the shared service executes asynchronously."""
        if self._closed or self._view is None or not self._online():
            return
        target = max(0, min(100, volume_percent))
        self._pending_volume = target
        self._volume_until = time.monotonic() + 1.5
        self._state = replace(self._state, media=replace(self._state.media, volume_percent=target))
        self._publish()
        try:
            self._set_volume(target)
        except Exception:
            self._pending_volume = None
            self._state = replace(self._state, message="Volume control unavailable")
            self._publish()

    def request_watch_video(self) -> None:
        if not self._state.video_available or self._state.video_busy:
            return
        self._video_action(False)

    def request_return_to_spotify(self) -> None:
        if self._state.video_busy:
            return
        self._video_action(True)

    def _video_action(self, returning: bool) -> None:
        if self._closed or self._view is None or not self._online():
            return
        self._returning_video = returning
        generation, track = self._generation, self._track_generation
        def current() -> bool:
            return (not self._closed and self._view is not None and self._online()
                    and generation == self._generation and track == self._track_generation)
        self._state = replace(self._state, video_busy=True, video_active=False if returning else self._state.video_active, message="Finding video..." if not returning else "Returning to Spotify…")
        self._publish()
        def work() -> Callable[[], None]:
            try:
                if returning:
                    self._return(current)
                    message = "Returned to Spotify"
                else:
                    message = "Music video playing" if self._watch_video(current, lambda: not self._closed and self._online()) else "No suitable music video found"
            except Exception as error:
                message = f"Video failed: {error}"
            def finish() -> None:
                self._returning_video = False
                self._state = replace(self._state, video_busy=False, video_active=self._video_active(), message=message)
            return finish
        self._work(work)
