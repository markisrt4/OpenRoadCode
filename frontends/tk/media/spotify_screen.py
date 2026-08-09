"""Tkinter screen for generic media playback presented by Spotify."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

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
    ) -> None:
        super().__init__(ScreenId("spotify"))
        self._host = host
        self._theme = theme
        self._back_action = back_action
        self._state: MediaState | None = None
        self._playback_handler: PlaybackRequestHandlerIf | None = None
        self._track_handler: TrackRequestHandlerIf | None = None
        self._seek_handler: SeekRequestHandlerIf | None = None
        self._volume_handler: VolumeRequestHandlerIf | None = None
        self._refresh_callback: Callable[[], object] | None = None
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

    def set_refresh_callback(
        self,
        callback: Callable[[], object] | None,
    ) -> None:
        """Set the application callback used to request fresh media state."""
        self._refresh_callback = callback

    def hide(self) -> None:
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
        )
        panel.set_playback_request_handler(self._playback_handler)
        panel.set_track_request_handler(self._track_handler)
        panel.set_seek_request_handler(self._seek_handler)
        panel.set_volume_request_handler(self._volume_handler)
        panel.set_media_state(self._state)
        panel.pack(fill="both", expand=True)

        self.spotify_panel = panel
        self._refresh()
        self._host.set_screen_status("Spotify controls ready")

    def _refresh(self) -> None:
        self._refresh_job = None
        callback = self._refresh_callback
        if callback is not None:
            callback()

        if self.spotify_panel is not None:
            self._refresh_job = self._host.schedule_ui_callback(
                self._theme["layout"]["refresh_interval_ms"],
                self._refresh,
            )
