# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Integrated media hub for the ORC UI shell."""

from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable

from apps.common.spotify_controller_factory import create_spotify_controller
from apps.common.uiTheme.spotify import SPOTIFY_PANEL_THEME
from apps.orcUi.orc_theme import (
    ACCENT_BLUE,
    ACCENT_GREEN,
    ACCENT_RED,
    DARK,
)
from config.runtime_target import RuntimeTarget, detect_runtime_target
from controllers.image import ImageCache
from controllers.lyrics import LrclibLyricsClient
from controllers.spotify import SpotifyMediaPresenter
from controllers.video import (
    MusicVideoController,
    NetflixPlayer,
    YouTubeMusicVideo,
    YouTubePlayer,
)
from frontends.tk.media import SpotifyPlaybackPanel


BG = DARK["bg"]
PANEL = DARK["panel"]
BORDER = DARK["border"]
TEXT = DARK["text"]
MUTED = DARK["muted"]


class _SpotifyPanelUi:
    """Small MediaUi adapter that lets the existing presenter drive a panel."""

    def __init__(self, panel: SpotifyPlaybackPanel) -> None:
        self._panel = panel

    def set_media_state(self, state) -> None:
        self._panel.set_media_state(state)


class MediaPanel(tk.Frame):
    """ORC-styled media landing page and hosted Spotify component."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        on_back: Callable[[], None],
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, bg=BG)
        self._on_back = on_back
        self._status_callback = status_callback or (lambda _message: None)
        self._view_host: tk.Frame | None = None
        self._active_component: tk.Widget | None = None
        self._netflix_player: NetflixPlayer | None = None
        self._youtube_player: YouTubePlayer | None = None
        self._spotify_video_controller: MusicVideoController | None = None
        self._spotify_refresh_job: str | None = None
        self._spotify_presenter: SpotifyMediaPresenter | None = None
        self._closed = False
        self._build_shell()
        self.show_hub()

    def close(self) -> None:
        """Stop media launched by this panel and cancel UI refresh work."""
        if self._closed:
            return
        self._closed = True
        if self._spotify_refresh_job is not None:
            try:
                self.after_cancel(self._spotify_refresh_job)
            except tk.TclError:
                pass
            self._spotify_refresh_job = None
        if self._spotify_video_controller is not None:
            self._spotify_video_controller.stop_video()
        if self._netflix_player is not None:
            self._netflix_player.stop()
        if self._youtube_player is not None:
            self._youtube_player.stop()

    def destroy(self) -> None:
        self.close()
        super().destroy()

    def show_hub(self) -> None:
        self._clear_view()
        self._set_title("MEDIA", "Streaming, playback, and video")

        grid = tk.Frame(self._view_host, bg=BG)
        grid.pack(fill=tk.BOTH, expand=True, padx=4, pady=(6, 4))
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1, uniform="media")
        grid.grid_rowconfigure(0, weight=1)

        cards = (
            (
                "SPOTIFY",
                "Music + playback",
                "Now playing, transport controls, artwork, lyrics, and music video.",
                ACCENT_GREEN,
                self.show_spotify,
            ),
            (
                "YOUTUBE",
                "Video + search",
                "Open YouTube directly in the dedicated ORC browser session.",
                ACCENT_RED,
                self.show_youtube,
            ),
            (
                "NETFLIX",
                "Streaming video",
                "Open Netflix directly with the retained ORC browser profile.",
                ACCENT_BLUE,
                self.show_netflix,
            ),
        )
        for column, card in enumerate(cards):
            self._media_card(grid, *card).grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=6,
                pady=6,
            )

    def show_spotify(self) -> None:
        self._clear_view()
        self._set_title("SPOTIFY", "Now playing and playback controls", show_media_back=True)
        try:
            controller = create_spotify_controller()
            image_cache = ImageCache(max_entries=64)
            lyrics_client = LrclibLyricsClient()
            target = detect_runtime_target()
            video_controller = MusicVideoController(
                spotify_controller=controller,
                music_video=YouTubeMusicVideo(
                    fullscreen=True,
                    software_rendering=target is RuntimeTarget.LINUX_DEV,
                ),
            )
            panel = SpotifyPlaybackPanel(
                self._view_host,
                music_video_controller=video_controller,
                image_cache=image_cache,
                lyrics_client=lyrics_client,
                theme=SPOTIFY_PANEL_THEME,
            )
            ui = _SpotifyPanelUi(panel)
            presenter = SpotifyMediaPresenter(controller, ui)
            panel.set_playback_request_handler(presenter)
            panel.set_track_request_handler(presenter)
            panel.set_seek_request_handler(presenter)
            panel.set_volume_request_handler(presenter)
            panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            self._active_component = panel
            self._spotify_video_controller = video_controller
            self._spotify_presenter = presenter
            self._refresh_spotify()
        except Exception as error:
            self._show_error("Spotify", error)

    def show_youtube(self) -> None:
        """Launch YouTube directly; the media hub remains underneath."""
        try:
            player = self._youtube_player or YouTubePlayer(
                software_rendering=detect_runtime_target() is RuntimeTarget.LINUX_DEV,
            )
            self._youtube_player = player
            player.play(
                "https://www.youtube.com/",
                display=os.environ.get("DISPLAY", ":1"),
            )
            self._status_callback("YouTube opened")
        except Exception as error:
            self._status_callback(f"YouTube failed: {error}")

    def show_netflix(self) -> None:
        """Launch Netflix directly; the media hub remains underneath."""
        try:
            player = self._netflix_player or NetflixPlayer(
                software_rendering=detect_runtime_target() is RuntimeTarget.LINUX_DEV,
            )
            self._netflix_player = player
            player.play(
                "https://www.netflix.com/browse",
                display=os.environ.get("DISPLAY", ":1"),
            )
            self._status_callback("Netflix opened")
        except Exception as error:
            self._status_callback(f"Netflix failed: {error}")

    def _build_shell(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._header = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        self._header.grid(row=0, column=0, sticky="ew", padx=2, pady=(2, 6))
        self._header.grid_columnconfigure(1, weight=1)
        self._back_button = tk.Button(
            self._header,
            text="‹ HOME",
            command=self._on_back,
            bg=PANEL,
            fg=TEXT,
            activebackground=DARK["active"],
            activeforeground=TEXT,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 10, "bold"),
            padx=10,
            pady=8,
        )
        self._back_button.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(6, 10), pady=5)
        self._title_label = tk.Label(
            self._header,
            text="MEDIA",
            bg=PANEL,
            fg=TEXT,
            font=("Sans", 16, "bold"),
        )
        self._title_label.grid(row=0, column=1, sticky="sw", pady=(7, 0))
        self._subtitle_label = tk.Label(
            self._header,
            text="",
            bg=PANEL,
            fg=MUTED,
            font=("Sans", 9),
        )
        self._subtitle_label.grid(row=1, column=1, sticky="nw", pady=(0, 7))

        self._media_back = tk.Button(
            self._header,
            text="ALL MEDIA",
            command=self.show_hub,
            bg=DARK["active"],
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 9, "bold"),
            padx=12,
            pady=7,
        )
        self._media_back.grid(row=0, column=2, rowspan=2, padx=8, pady=6)

        self._view_host = tk.Frame(self, bg=BG)
        self._view_host.grid(row=1, column=0, sticky="nsew")

    def _set_title(self, title: str, subtitle: str, *, show_media_back: bool = False) -> None:
        self._title_label.configure(text=title)
        self._subtitle_label.configure(text=subtitle)
        if show_media_back:
            self._media_back.grid()
        else:
            self._media_back.grid_remove()

    def _clear_view(self) -> None:
        if self._spotify_refresh_job is not None:
            try:
                self.after_cancel(self._spotify_refresh_job)
            except tk.TclError:
                pass
            self._spotify_refresh_job = None
        self._spotify_presenter = None
        if self._spotify_video_controller is not None:
            self._spotify_video_controller.stop_video()
            self._spotify_video_controller = None
        self._active_component = None
        if self._view_host is not None:
            for child in self._view_host.winfo_children():
                child.destroy()

    def _refresh_spotify(self) -> None:
        presenter = self._spotify_presenter
        if presenter is None or self._closed:
            return
        try:
            presenter.refresh()
        except Exception as error:
            self._status_callback(f"Spotify refresh failed: {error}")
        self._spotify_refresh_job = self.after(5000, self._refresh_spotify)

    def _media_card(
        self,
        parent: tk.Widget,
        title: str,
        subtitle: str,
        detail: str,
        accent: str,
        command: Callable[[], None],
    ) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=PANEL,
            highlightthickness=1,
            highlightbackground=BORDER,
            cursor="hand2",
        )
        accent_bar = tk.Frame(card, bg=accent, height=5)
        accent_bar.pack(fill=tk.X)
        body = tk.Frame(card, bg=PANEL)
        body.pack(fill=tk.BOTH, expand=True, padx=18, pady=16)
        tk.Label(
            body,
            text=title,
            bg=PANEL,
            fg=accent,
            font=("Sans", 18, "bold"),
        ).pack(anchor="w", pady=(4, 8))
        tk.Label(
            body,
            text=subtitle,
            bg=PANEL,
            fg=TEXT,
            font=("Sans", 12, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        tk.Label(
            body,
            text=detail,
            bg=PANEL,
            fg=MUTED,
            font=("Sans", 9),
            justify=tk.LEFT,
            wraplength=230,
        ).pack(anchor="w")
        tk.Button(
            body,
            text="OPEN",
            command=command,
            bg=DARK["active"],
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 10, "bold"),
            padx=14,
            pady=8,
        ).pack(anchor="w", side=tk.BOTTOM, pady=(14, 0))
        self._bind_card(card, command)
        return card

    @staticmethod
    def _bind_card(widget: tk.Widget, command: Callable[[], None]) -> None:
        widget.bind("<Button-1>", lambda _event: command())
        for child in widget.winfo_children():
            if isinstance(child, tk.Button):
                continue
            MediaPanel._bind_card(child, command)

    def _show_error(self, service: str, error: Exception) -> None:
        self._status_callback(f"{service} failed: {error}")
        tk.Label(
            self._view_host,
            text=f"{service} unavailable\n\n{error}",
            bg=BG,
            fg=TEXT,
            font=("Sans", 15, "bold"),
            justify=tk.CENTER,
            wraplength=650,
        ).place(relx=0.5, rely=0.5, anchor="center")
