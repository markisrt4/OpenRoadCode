# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tkinter screen for Spotify playback and browsing."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable
from typing import Any

from apps.orcUi.spotify_local_player import SpotifyLocalPlayer
from apps.orcUi.spotify_state_service import SpotifyStateService
from frontends.tk.media.spotify_browse_panel import SpotifyBrowsePanel
from frontends.tk.media.spotify_services_if import ArtworkProviderIf, LyricsProviderIf, MusicVideoRequestHandlerIf
from frontends.tk.media.spotify_playback_panel import SpotifyPlaybackPanel
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.media import MediaState, MediaUiIf, PlaybackRequestHandlerIf, SeekRequestHandlerIf, TrackRequestHandlerIf, VolumeRequestHandlerIf
from ui.screen_ui_if import ScreenId


class _ThreadSafeSpotifyPlaybackPanel(SpotifyPlaybackPanel):
    """Route worker-thread callbacks through a Python-only callback queue."""

    def __init__(self, *args, ui_dispatch: Callable[[Callable[[], None]], None], **kwargs) -> None:
        self._ui_dispatch = ui_dispatch
        self._tk_thread_id = threading.get_ident()
        super().__init__(*args, **kwargs)

    def after(self, ms: int, func=None, *args):
        if threading.get_ident() != self._tk_thread_id:
            if func is None or ms != 0:
                raise RuntimeError("worker threads may only dispatch immediate UI callbacks")
            self._ui_dispatch(lambda: func(*args))
            return None
        return super().after(ms, func, *args)


class SpotifyScreen(TkScreen, MediaUiIf):
    """Present Spotify now-playing, destination selection, and library browse."""

    def __init__(self, host: TkScreenHostIf, *, theme: dict[str, Any], back_action: Callable[[], None], image_cache: ArtworkProviderIf, lyrics_client: LyricsProviderIf, music_video_controller: MusicVideoRequestHandlerIf, service: SpotifyStateService | None = None, local_player: SpotifyLocalPlayer | None = None) -> None:
        super().__init__(ScreenId("spotify"))
        self._host = host
        self._theme = theme
        self._back_action = back_action
        self._image_cache = image_cache
        self._lyrics_client = lyrics_client
        self._music_video_controller = music_video_controller
        self._service = service
        self._local_player = local_player
        self._state: MediaState | None = None
        self._playback_handler: PlaybackRequestHandlerIf | None = None
        self._track_handler: TrackRequestHandlerIf | None = None
        self._seek_handler: SeekRequestHandlerIf | None = None
        self._volume_handler: VolumeRequestHandlerIf | None = None
        self._state_loader: Callable[[], MediaState] | None = None
        self._state_results: queue.SimpleQueue[tuple[int, MediaState]] = queue.SimpleQueue()
        self._ui_callbacks: queue.SimpleQueue[Callable[[], None]] = queue.SimpleQueue()
        self._refresh_generation = 0
        self._refresh_job: object | None = None
        self._dispatch_job: object | None = None
        self.spotify_panel: SpotifyPlaybackPanel | None = None

    def set_media_state(self, state: MediaState | None) -> None:
        self._state = state
        if self.spotify_panel is not None:
            self.spotify_panel.set_media_state(state)

    def set_playback_request_handler(self, handler: PlaybackRequestHandlerIf | None) -> None:
        self._playback_handler = handler
        if self.spotify_panel is not None:
            self.spotify_panel.set_playback_request_handler(handler)

    def set_track_request_handler(self, handler: TrackRequestHandlerIf | None) -> None:
        self._track_handler = handler
        if self.spotify_panel is not None:
            self.spotify_panel.set_track_request_handler(handler)

    def set_seek_request_handler(self, handler: SeekRequestHandlerIf | None) -> None:
        self._seek_handler = handler
        if self.spotify_panel is not None:
            self.spotify_panel.set_seek_request_handler(handler)

    def set_volume_request_handler(self, handler: VolumeRequestHandlerIf | None) -> None:
        self._volume_handler = handler
        if self.spotify_panel is not None:
            self.spotify_panel.set_volume_request_handler(handler)

    def set_state_loader(self, loader: Callable[[], MediaState] | None) -> None:
        self._state_loader = loader

    def _dispatch_ui(self, callback: Callable[[], None]) -> None:
        """Worker-safe dispatch. This method never calls into Tcl."""
        self._ui_callbacks.put(callback)

    def _poll_ui_callbacks(self, generation: int) -> None:
        self._dispatch_job = None
        if generation != self._refresh_generation:
            return
        while True:
            try:
                callback = self._ui_callbacks.get_nowait()
            except queue.Empty:
                break
            callback()
        self._dispatch_job = self._host.schedule_ui_callback(25, lambda: self._poll_ui_callbacks(generation))

    def hide(self) -> None:
        self._refresh_generation += 1
        for job_name in ("_refresh_job", "_dispatch_job"):
            job = getattr(self, job_name)
            if job is not None:
                try:
                    self._host.cancel_ui_callback(job)
                except Exception:
                    pass
                setattr(self, job_name, None)
        self.spotify_panel = None

    def show(self) -> None:
        self._show_now_playing()

    def _begin_screen(self) -> int:
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("Spotify")
        self._host.set_screen_back_action(self._back_action)
        generation = self._refresh_generation
        self._dispatch_job = self._host.schedule_ui_callback(25, lambda: self._poll_ui_callbacks(generation))
        return generation

    def _show_now_playing(self) -> None:
        generation = self._begin_screen()
        root = tk.Frame(self._host.screen_parent, bg="#121212")
        root.pack(fill=tk.BOTH, expand=True)

        if self._service is not None and self._local_player is not None:
            controls = SpotifyBrowsePanel(root, service=self._service, local_player=self._local_player, dispatch_ui=self._dispatch_ui, show_now_playing=self._show_now_playing)
            controls.pack(fill=tk.X)
            controls._content.pack_forget()
            controls._content.pack(fill=tk.X)
            controls._clear()
            controls._build_mode_bar()
            controls._build_browse_bar(active="now")

        panel = _ThreadSafeSpotifyPlaybackPanel(parent=root, theme=self._theme, image_cache=self._image_cache, lyrics_client=self._lyrics_client, music_video_controller=self._music_video_controller, ui_dispatch=self._dispatch_ui)
        panel.set_playback_request_handler(self._playback_handler)
        panel.set_track_request_handler(self._track_handler)
        panel.set_seek_request_handler(self._seek_handler)
        panel.set_volume_request_handler(self._volume_handler)
        panel.pack(fill=tk.BOTH, expand=True)
        self.spotify_panel = panel
        self._host.set_screen_status("Loading Spotify…")
        self._refresh_job = self._host.schedule_ui_callback(1, lambda: self._start_refresh(panel, generation))

    def _show_saved(self) -> None:
        self._show_browse(lambda panel: panel.show_saved())

    def _show_recent(self) -> None:
        self._show_browse(lambda panel: panel.show_recent())

    def _show_playlists(self) -> None:
        self._show_browse(lambda panel: panel.show_playlists())

    def _show_browse(self, action: Callable[[SpotifyBrowsePanel], None]) -> None:
        self._begin_screen()
        if self._service is None or self._local_player is None:
            return
        panel = SpotifyBrowsePanel(self._host.screen_parent, service=self._service, local_player=self._local_player, dispatch_ui=self._dispatch_ui, show_now_playing=self._show_now_playing)
        panel.pack(fill=tk.BOTH, expand=True)
        action(panel)

    def _start_refresh(self, panel: SpotifyPlaybackPanel, generation: int) -> None:
        self._refresh_job = None
        loader = self._state_loader
        if panel is not self.spotify_panel or generation != self._refresh_generation or loader is None:
            return
        threading.Thread(target=self._load_state_worker, args=(loader, generation), name="spotify-state", daemon=True).start()
        self._refresh_job = self._host.schedule_ui_callback(25, lambda: self._poll_state(panel, generation))

    def _load_state_worker(self, loader: Callable[[], MediaState], generation: int) -> None:
        self._state_results.put((generation, loader()))

    def _poll_state(self, panel: SpotifyPlaybackPanel, generation: int) -> None:
        self._refresh_job = None
        if panel is not self.spotify_panel or generation != self._refresh_generation:
            return
        while True:
            try:
                result_generation, state = self._state_results.get_nowait()
            except queue.Empty:
                self._refresh_job = self._host.schedule_ui_callback(25, lambda: self._poll_state(panel, generation))
                return
            if result_generation == generation:
                break
        self.set_media_state(state)
        self._host.set_screen_status("Spotify controls ready")
        self._refresh_job = self._host.schedule_ui_callback(self._theme["layout"]["refresh_interval_ms"], lambda: self._start_refresh(panel, generation))
