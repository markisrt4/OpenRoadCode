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
from ui.screen_ui_if import ScreenId

MediaNavigationFactory = Callable[[tk.Misc, str], tk.Widget]

SPOTIFY_GREEN = "#1DB954"


class SpotifyScreen(TkScreen, MediaUiIf):
    """Present Spotify now-playing, destination selection, and library browse."""

    def __init__(
        self, host: TkScreenHostIf, *, theme: dict[str, Any] | Callable[[], dict[str, Any]],
        back_action: Callable[[], None],
        media_navigation_factory: MediaNavigationFactory | None = None,
        spotify_configured: Callable[[], bool] | None = None,
        spotify_account_connected: Callable[[], bool] | None = None,
        configure_spotify: Callable[[], None] | None = None,
        connect_spotify: Callable[[], None] | None = None,
        disconnect_spotify: Callable[[], None] | None = None,
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
        self._spotify_configured = spotify_configured or (lambda: True)
        self._spotify_account_connected = spotify_account_connected or (lambda: True)
        self._configure_spotify = configure_spotify
        self._connect_spotify = connect_spotify
        self._disconnect_spotify = disconnect_spotify
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

    def _build_setup_banner(self, parent: tk.Misc) -> None:
        """Keep Spotify setup visible, and prominent when configuration is missing."""
        configured = self._spotify_configured()
        connected = self._spotify_account_connected()
        colors = self._theme["colors"]
        surface = colors.get("card_background", colors["background"])
        text = colors.get("title", "#FFFFFF")
        muted = colors.get("subtitle", text)
        button_bg = colors.get("button_background", surface)
        button_fg = colors.get("button_foreground", text)
        row = tk.Frame(parent, bg=surface)
        row.pack(fill=tk.X, padx=4, pady=(2, 4))

        if not configured:
            status = "Spotify setup required"
        elif not connected:
            status = "Spotify account not connected"
        else:
            status = "Spotify connected"

        tk.Label(
            row, text=status.upper(), bg=surface,
            fg=SPOTIFY_GREEN if configured and connected else muted,
            font=("Sans", 9, "bold"),
        ).pack(side=tk.LEFT, padx=10, pady=8)

        if self._configure_spotify is not None:
            tk.Button(
                row, text="CONFIGURE", command=self._configure_spotify,
                bg=button_bg, fg=button_fg,
                relief=tk.FLAT, bd=0, font=("Sans", 8, "bold"), padx=10, pady=5,
            ).pack(side=tk.RIGHT, padx=(4, 8), pady=5)

        account_action = self._disconnect_spotify if connected else self._connect_spotify
        if configured and account_action is not None:
            tk.Button(
                row, text="DISCONNECT" if connected else "CONNECT SPOTIFY",
                command=account_action,
                bg=button_bg if connected else SPOTIFY_GREEN,
                fg=button_fg if connected else "#000000",
                relief=tk.FLAT, bd=0, font=("Sans", 8, "bold"), padx=10, pady=5,
            ).pack(side=tk.RIGHT, padx=4, pady=5)

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
        self._host.set_screen_status(state.message or state.media.status_message or "Spotify controls ready")
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
