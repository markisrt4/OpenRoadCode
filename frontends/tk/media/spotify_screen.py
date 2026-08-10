"""Tkinter screen for generic media playback presented by Spotify."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from typing import Any

from frontends.tk.media.spotify_services_if import (
    ArtworkProviderIf,
    LyricsProviderIf,
    MusicVideoRequestHandlerIf,
)
from frontends.tk.media.spotify_playback_panel import SpotifyPlaybackPanel
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.media import (
    MediaState,
    MediaUiIf,
    PlaybackRequestHandlerIf,
    SeekRequestHandlerIf,
    TrackRequestHandlerIf,
    VolumeRequestHandlerIf,
)
from ui.screen_ui_if import ScreenId


class SpotifyScreen(TkScreen, MediaUiIf):
    """Present media state and connect media request handlers."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        theme: dict[str, Any],
        back_action: Callable[[], None],
        image_cache: ArtworkProviderIf,
        lyrics_client: LyricsProviderIf,
        music_video_controller: MusicVideoRequestHandlerIf,
    ) -> None:
        super().__init__(ScreenId("spotify"))
        self._host = host
        self._theme = theme
        self._back_action = back_action
        self._image_cache = image_cache
        self._lyrics_client = lyrics_client
        self._music_video_controller = music_video_controller
        self._state: MediaState | None = None
        self._playback_handler: PlaybackRequestHandlerIf | None = None
        self._track_handler: TrackRequestHandlerIf | None = None
        self._seek_handler: SeekRequestHandlerIf | None = None
        self._volume_handler: VolumeRequestHandlerIf | None = None
        self._state_loader: Callable[[], MediaState] | None = None
        self._state_results: queue.SimpleQueue[tuple[int, MediaState]] = (
            queue.SimpleQueue()
        )
        self._refresh_generation = 0
        self._refresh_job: object | None = None
        self.spotify_panel: SpotifyPlaybackPanel | None = None

    def set_media_state(self, state: MediaState | None) -> None:
        self._state = state
        if self.spotify_panel is not None:
            self.spotify_panel.set_media_state(state)

    def set_playback_request_handler(
        self,
        handler: PlaybackRequestHandlerIf | None,
    ) -> None:
        self._playback_handler = handler
        if self.spotify_panel is not None:
            self.spotify_panel.set_playback_request_handler(handler)

    def set_track_request_handler(
        self,
        handler: TrackRequestHandlerIf | None,
    ) -> None:
        self._track_handler = handler
        if self.spotify_panel is not None:
            self.spotify_panel.set_track_request_handler(handler)

    def set_seek_request_handler(
        self,
        handler: SeekRequestHandlerIf | None,
    ) -> None:
        self._seek_handler = handler
        if self.spotify_panel is not None:
            self.spotify_panel.set_seek_request_handler(handler)

    def set_volume_request_handler(
        self,
        handler: VolumeRequestHandlerIf | None,
    ) -> None:
        self._volume_handler = handler
        if self.spotify_panel is not None:
            self.spotify_panel.set_volume_request_handler(handler)

    def set_state_loader(
        self,
        loader: Callable[[], MediaState] | None,
    ) -> None:
        """Set the backend loader used by asynchronous refreshes.

        @param loader Callable that reads and returns the latest media state
            without touching Tk widgets.
        """
        self._state_loader = loader

    def hide(self) -> None:
        self._refresh_generation += 1
        if self._refresh_job is not None:
            try:
                self._host.cancel_ui_callback(self._refresh_job)
            except Exception:
                pass
            self._refresh_job = None

    def show(self) -> None:
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("Spotify")
        self._host.set_screen_back_action(self._back_action)

        panel = SpotifyPlaybackPanel(
            parent=self._host.screen_parent,
            theme=self._theme,
            image_cache=self._image_cache,
            lyrics_client=self._lyrics_client,
            music_video_controller=self._music_video_controller,
        )
        panel.set_playback_request_handler(self._playback_handler)
        panel.set_track_request_handler(self._track_handler)
        panel.set_seek_request_handler(self._seek_handler)
        panel.set_volume_request_handler(self._volume_handler)
        panel.pack(fill="both", expand=True)

        self.spotify_panel = panel
        self._host.set_screen_status("Loading Spotify…")
        generation = self._refresh_generation
        self._refresh_job = self._host.schedule_ui_callback(
            1,
            lambda: self._start_refresh(panel, generation),
        )

    def _start_refresh(
        self,
        panel: SpotifyPlaybackPanel,
        generation: int,
    ) -> None:
        """Read Spotify state off the Tk event-loop thread."""
        self._refresh_job = None
        loader = self._state_loader
        if (
            panel is not self.spotify_panel
            or generation != self._refresh_generation
            or loader is None
        ):
            return
        threading.Thread(
            target=self._load_state_worker,
            args=(loader, generation),
            name="spotify-state",
            daemon=True,
        ).start()
        self._refresh_job = self._host.schedule_ui_callback(
            25,
            lambda: self._poll_state(panel, generation),
        )

    def _load_state_worker(
        self,
        loader: Callable[[], MediaState],
        generation: int,
    ) -> None:
        self._state_results.put((generation, loader()))

    def _poll_state(
        self,
        panel: SpotifyPlaybackPanel,
        generation: int,
    ) -> None:
        self._refresh_job = None
        if (
            panel is not self.spotify_panel
            or generation != self._refresh_generation
        ):
            return
        while True:
            try:
                result_generation, state = self._state_results.get_nowait()
            except queue.Empty:
                self._refresh_job = self._host.schedule_ui_callback(
                    25,
                    lambda: self._poll_state(panel, generation),
                )
                return
            if result_generation == generation:
                break
        self.set_media_state(state)
        self._host.set_screen_status("Spotify controls ready")
        self._refresh_job = self._host.schedule_ui_callback(
            self._theme["layout"]["refresh_interval_ms"],
            lambda: self._start_refresh(panel, generation),
        )
