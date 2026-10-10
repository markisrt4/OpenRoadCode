# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tkinter screen for Spotify playback and browsing."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any

from frontends.tk.media.spotify_browse_panel import SpotifyBrowsePanel
from frontends.tk.media.spotify_playback_panel import SpotifyPlaybackPanel
from ui.media.spotify_browse_if import SpotifyBrowseSession
from frontends.tk.media.spotify_video_overlay import SpotifyVideoOverlay
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.media import MediaState, MediaUiIf, PlaybackRequestHandlerIf, SeekRequestHandlerIf, TrackRequestHandlerIf, VolumeRequestHandlerIf
from ui.media.spotify_presentation_if import SpotifyNativeSurface, SpotifyPresentationSession, SpotifyPresentationState, SpotifyVideoRequests, SpotifyRequestHandler
from ui.media.spotify_account_if import SpotifyAccountRequests, SpotifyAccountSession, SpotifyAccountState
from ui.screen_ui_if import ScreenId

MediaNavigationFactory = Callable[[tk.Misc, str], tk.Widget]

SPOTIFY_GREEN = "#1DB954"


class SpotifyScreen(TkScreen, MediaUiIf):
    """Present Spotify now-playing, destination selection, and library browse."""

    def __init__(
        self, host: TkScreenHostIf, *, theme: dict[str, Any] | Callable[[], dict[str, Any]],
        back_action: Callable[[], None],
        media_navigation_factory: MediaNavigationFactory | None = None,
        account_session: SpotifyAccountSession | None = None,
        show_account_configuration: Callable[[], None] | None = None,
        close_account_configuration: Callable[[], None] = lambda: None,
        playback_session: SpotifyPresentationSession,
        native_surface: SpotifyNativeSurface,
        browse_session: SpotifyBrowseSession | None = None,
    ) -> None:
        super().__init__(ScreenId("spotify"))
        self._browse_session = browse_session
        self._native_surface = native_surface
        self._playback_session = playback_session
        self._host = host
        self._theme_provider = theme if callable(theme) else lambda: theme
        self._theme = self._theme_provider()
        self._back_action = back_action
        self._media_navigation_factory = media_navigation_factory
        self._account_session = account_session
        self._show_account_configuration = show_account_configuration
        self._close_account_configuration = close_account_configuration
        self._account_handler: SpotifyAccountRequests | None = None
        self._account = SpotifyAccountState()
        self._account_label: tk.Label | None = None
        self._account_button: tk.Button | None = None
        self._configuration_button: tk.Button | None = None
        self._state: MediaState | None = None
        self._playback_handler: PlaybackRequestHandlerIf | None = None
        self._track_handler: TrackRequestHandlerIf | None = None
        self._seek_handler: SeekRequestHandlerIf | None = None
        self._volume_handler: VolumeRequestHandlerIf | None = None
        self._video_overlay: SpotifyVideoOverlay | None = None
        self.spotify_panel: SpotifyPlaybackPanel | None = None
        self._visible = False
        self._view = "now"
        self._browse_action: Callable[[SpotifyBrowsePanel], None] | None = None
        self._browse_panel_view: SpotifyBrowsePanel | None = None

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

    def set_theme_mode(self, _mode: object) -> None:
        """Rebuild the current view without changing playback or browser ownership."""
        if not self._visible:
            return
        if self._view == "browse" and self._browse_action is not None:
            self._show_browse(self._browse_action)
        else:
            self._show_now_playing()

    def hide(self) -> None:
        self._visible = False
        if self._account_session is not None:
            self._account_session.deactivate()
        self._close_account_configuration()
        self._account_label = None
        self._account_button = None
        self._configuration_button = None
        self._playback_session.deactivate()
        if self._browse_session is not None:
            self._browse_session.deactivate()
        self._browse_panel_view = None
        if self._video_overlay is not None:
            self._video_overlay.close()
            self._video_overlay = None
        self.spotify_panel = None

    def show(self) -> None:
        self._show_now_playing()

    def _begin_screen(self) -> None:
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._visible = True
        self._theme = self._theme_provider()
        self._host.set_screen_title("Spotify")
        self._host.set_screen_back_action(self._back_action)

    def _build_media_navigation(self, parent: tk.Misc) -> None:
        if self._media_navigation_factory is not None:
            self._media_navigation_factory(parent, "spotify").pack(fill=tk.X, padx=4, pady=(4, 2))

    def set_spotify_account_handler(self, handler: SpotifyAccountRequests | None) -> None:
        self._account_handler = handler

    def set_spotify_account_state(self, state: SpotifyAccountState) -> None:
        self._account = state
        if self._account_label is not None:
            text = "Spotify setup required" if not state.configured else "Spotify connected" if state.connected else "Spotify account not connected"
            self._account_label.configure(text=text.upper())
        if self._account_button is not None:
            self._account_button.configure(text="DISCONNECT" if state.connected else "CONNECT SPOTIFY",
                state=tk.DISABLED if state.busy or state.loading or not state.configured or not (state.online or state.connected) else tk.NORMAL)
        if self._configuration_button is not None:
            self._configuration_button.configure(state=tk.DISABLED if state.busy else tk.NORMAL)
        if state.message:
            self._host.set_screen_status(state.message)

    def _request_account_action(self) -> None:
        handler = self._account_handler
        if handler is not None:
            if self._account.connected:
                handler.request_disconnect()
            else:
                handler.request_connect()

    def _build_setup_banner(self, parent: tk.Misc) -> None:
        colors = self._theme["colors"]
        surface = colors.get("card_background", colors["background"])
        text = colors.get("title", "#FFFFFF")
        button_bg = colors.get("button_background", surface)
        button_fg = colors.get("button_foreground", text)
        row = tk.Frame(parent, bg=surface)
        row.pack(fill=tk.X, padx=4, pady=(2, 4))
        self._account_label = tk.Label(row, text="SPOTIFY", bg=surface, fg=SPOTIFY_GREEN,
            font=("Sans", 9, "bold"))
        self._account_label.pack(side=tk.LEFT, padx=10, pady=8)
        if self._show_account_configuration is not None:
            self._configuration_button = tk.Button(row, text="CONFIGURE", command=self._show_account_configuration,
                bg=button_bg, fg=button_fg, relief=tk.FLAT, bd=0, font=("Sans", 8, "bold"), padx=10, pady=5)
            self._configuration_button.pack(side=tk.RIGHT, padx=(4, 8), pady=5)
        if self._account_session is not None:
            self._account_button = tk.Button(row, text="CONNECT SPOTIFY", command=self._request_account_action,
                bg=button_bg, fg=button_fg, relief=tk.FLAT, bd=0, font=("Sans", 8, "bold"), padx=10, pady=5)
            self._account_button.pack(side=tk.RIGHT, padx=4, pady=5)
        if self._account_session is not None:
            self.set_spotify_account_state(self._account)

    def _browse_panel(self, parent: tk.Misc) -> SpotifyBrowsePanel:
        if self._browse_session is None:
            raise RuntimeError("Spotify browsing is unavailable")
        panel = SpotifyBrowsePanel(parent, show_now_playing=self._show_now_playing, theme=self._theme)
        self._browse_panel_view = panel
        self._browse_session.activate(panel)
        return panel

    def _show_now_playing(self) -> None:
        self._begin_screen()
        self._view = "now"
        self._browse_action = None
        root = tk.Frame(self._host.screen_parent, bg=self._theme["colors"]["background"])
        root.pack(fill=tk.BOTH, expand=True)
        self._build_media_navigation(root)
        self._build_setup_banner(root)
        if self._account_session is not None:
            self._account_session.activate(self)
        if self._browse_session is not None:
            controls = self._browse_panel(root)
            controls.pack(fill=tk.X)
            controls.show_now_playing_header()
        content = tk.Frame(root, bg=self._theme["colors"]["background"])
        content.pack(fill=tk.BOTH, expand=True)
        panel = SpotifyPlaybackPanel(parent=content, theme=self._theme)
        panel.set_playback_request_handler(self._playback_handler)
        panel.set_track_request_handler(self._track_handler)
        panel.set_seek_request_handler(self._seek_handler)
        panel.set_volume_request_handler(self._volume_handler)
        panel.pack(fill=tk.BOTH, expand=True)
        self.spotify_panel = panel
        if self._state is not None:
            panel.set_media_state(self._state)
        self._video_overlay = SpotifyVideoOverlay(
            content, native_surface=self._native_surface,
            set_status=self._host.set_screen_status,
        )
        self._host.set_screen_status("Loading Spotify…")
        self._playback_session.activate(self)

    def _show_browse(self, action: Callable[[SpotifyBrowsePanel], None]) -> None:
        self._begin_screen()
        self._view = "browse"
        self._browse_action = action
        root = tk.Frame(self._host.screen_parent, bg=self._theme["colors"]["background"])
        root.pack(fill=tk.BOTH, expand=True)
        self._build_media_navigation(root)
        if self._browse_session is None:
            return
        panel = self._browse_panel(root)
        panel.pack(fill=tk.BOTH, expand=True)
        action(panel)

    def set_spotify_state(self, state: SpotifyPresentationState) -> None:
        self._state = state.media
        self._host.set_screen_status(self._account.message if self._account.busy or self._account.error else state.message or state.media.status_message or "Spotify controls ready")
        if self.spotify_panel is not None:
            self.spotify_panel.set_spotify_state(state)
        if self._video_overlay is not None:
            self._video_overlay.sync(state)

    def set_spotify_request_handler(self, handler: SpotifyRequestHandler | None) -> None:
        self.set_playback_request_handler(handler)
        self.set_track_request_handler(handler)
        self.set_seek_request_handler(handler)
        self.set_volume_request_handler(handler)
        self.set_video_request_handler(handler)

    def set_video_request_handler(self, handler: SpotifyVideoRequests | None) -> None:
        if self.spotify_panel is not None:
            self.spotify_panel.set_video_request_handler(handler)
        if self._video_overlay is not None:
            self._video_overlay.set_video_request_handler(handler)
