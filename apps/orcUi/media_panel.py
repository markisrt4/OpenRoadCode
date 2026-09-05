# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Integrated media hub for the ORC UI shell."""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from collections.abc import Callable

from apps.common.spotify_controller_factory import create_spotify_controller
from apps.common.uiTheme.spotify import SPOTIFY_PANEL_THEME
from apps.orcUi.orc_theme import ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED, DARK
from config.runtime_target import RuntimeTarget, detect_runtime_target
from controllers.image import ImageCache
from controllers.lyrics import LrclibLyricsClient
from controllers.spotify import SpotifyMediaPresenter
from controllers.video import MusicVideoController, NetflixPlayer, YouTubeMusicVideo, YouTubePlayer
from frontends.tk.media import SpotifyPlaybackPanel
from ui.media import MediaState

BG = DARK["bg"]
PANEL = DARK["panel"]
ACTIVE = DARK["active"]
BORDER = DARK["border"]
TEXT = DARK["text"]
MUTED = DARK["muted"]


class _ThreadSafeSpotifyPlaybackPanel(SpotifyPlaybackPanel):
    """Keep worker-thread panel callbacks out of Tcl/Tk."""

    def __init__(
        self,
        *args,
        ui_dispatch: Callable[[Callable[[], None]], None],
        **kwargs,
    ) -> None:
        self._ui_dispatch = ui_dispatch
        self._tk_thread_id = threading.get_ident()
        super().__init__(*args, **kwargs)

    def after(self, ms: int, func=None, *args):
        if threading.get_ident() != self._tk_thread_id:
            if func is None:
                raise RuntimeError("worker threads may not call Tk after() without a callback")
            if ms != 0:
                raise RuntimeError("worker threads may only dispatch immediate UI callbacks")
            self._ui_dispatch(lambda: func(*args))
            return None
        return super().after(ms, func, *args)


class _SpotifyPanelUi:
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
        self._netflix_player: NetflixPlayer | None = None
        self._youtube_player: YouTubePlayer | None = None
        self._spotify_video_controller: MusicVideoController | None = None
        self._spotify_refresh_job: str | None = None
        self._spotify_presenter: SpotifyMediaPresenter | None = None
        self._spotify_panel: SpotifyPlaybackPanel | None = None
        self._spotify_refresh_generation = 0
        self._spotify_refresh_in_flight = False
        self._spotify_state_results: queue.SimpleQueue[tuple[int, MediaState]] = queue.SimpleQueue()
        self._ui_dispatch_queue: queue.SimpleQueue[Callable[[], None]] = queue.SimpleQueue()
        self._ui_dispatch_job: str | None = None
        self._closed = False
        self._build_shell()
        self._ui_dispatch_job = self.after(25, self._poll_ui_dispatch)
        self.show_hub()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._cancel_spotify_refresh()
        if self._ui_dispatch_job is not None:
            try:
                self.after_cancel(self._ui_dispatch_job)
            except tk.TclError:
                pass
            self._ui_dispatch_job = None
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
        self._set_title("MEDIA", "Music, video, and streaming")

        hero = tk.Frame(self._view_host, bg=BG)
        hero.pack(fill=tk.X, padx=12, pady=(2, 4))
        tk.Label(
            hero,
            text="YOUR MEDIA",
            bg=BG,
            fg=TEXT,
            font=("Sans", 22, "bold"),
        ).pack(anchor="w")
        tk.Label(
            hero,
            text="Pick a service and go. No launcher maze required.",
            bg=BG,
            fg=MUTED,
            font=("Sans", 10),
        ).pack(anchor="w", pady=(1, 0))

        grid = tk.Frame(self._view_host, bg=BG)
        grid.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 8))
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1, uniform="media")
        grid.grid_rowconfigure(0, weight=1)

        cards = (
            (
                "♫",
                "SPOTIFY",
                "MUSIC",
                "Now playing",
                "Artwork, lyrics, playback controls and music video.",
                "OPEN PLAYER",
                ACCENT_GREEN,
                self.show_spotify,
            ),
            (
                "▶",
                "YOUTUBE",
                "VIDEO",
                "Watch anything",
                "Jump straight into your dedicated YouTube session.",
                "OPEN YOUTUBE",
                ACCENT_RED,
                self.show_youtube,
            ),
            (
                "N",
                "NETFLIX",
                "STREAM",
                "Continue watching",
                "Launch Netflix with your retained browser profile.",
                "OPEN NETFLIX",
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
                pady=4,
            )

    def show_spotify(self) -> None:
        self._clear_view()
        self._set_title("SPOTIFY", "Now playing and playback controls", show_media_back=True)
        try:
            controller = create_spotify_controller()
            target = detect_runtime_target()
            video_controller = MusicVideoController(
                spotify_controller=controller,
                music_video=YouTubeMusicVideo(
                    fullscreen=True,
                    software_rendering=target is RuntimeTarget.LINUX_DEV,
                ),
            )
            panel = _ThreadSafeSpotifyPlaybackPanel(
                self._view_host,
                music_video_controller=video_controller,
                image_cache=ImageCache(max_entries=64),
                lyrics_client=LrclibLyricsClient(),
                theme=SPOTIFY_PANEL_THEME,
                ui_dispatch=self._dispatch_ui,
            )
            presenter = SpotifyMediaPresenter(controller, _SpotifyPanelUi(panel))
            panel.set_playback_request_handler(presenter)
            panel.set_track_request_handler(presenter)
            panel.set_seek_request_handler(presenter)
            panel.set_volume_request_handler(presenter)
            panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            self._spotify_video_controller = video_controller
            self._spotify_presenter = presenter
            self._spotify_panel = panel
            self._refresh_spotify()
        except Exception as error:
            self._show_error("Spotify", error)

    def show_youtube(self) -> None:
        try:
            player = self._youtube_player or YouTubePlayer(
                software_rendering=detect_runtime_target() is RuntimeTarget.LINUX_DEV,
            )
            self._youtube_player = player
            player.play("https://www.youtube.com/", display=os.environ.get("DISPLAY", ":1"))
            self._status_callback("YouTube opened")
        except Exception as error:
            self._status_callback(f"YouTube failed: {error}")

    def show_netflix(self) -> None:
        try:
            player = self._netflix_player or NetflixPlayer(
                software_rendering=detect_runtime_target() is RuntimeTarget.LINUX_DEV,
            )
            self._netflix_player = player
            player.play("https://www.netflix.com/browse", display=os.environ.get("DISPLAY", ":1"))
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
            activebackground=ACTIVE,
            activeforeground=TEXT,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 10, "bold"),
            padx=10,
            pady=8,
        )
        self._back_button.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(6, 10), pady=5)

        self._title_label = tk.Label(self._header, text="MEDIA", bg=PANEL, fg=TEXT, font=("Sans", 16, "bold"))
        self._title_label.grid(row=0, column=1, sticky="sw", pady=(7, 0))
        self._subtitle_label = tk.Label(self._header, text="", bg=PANEL, fg=MUTED, font=("Sans", 9))
        self._subtitle_label.grid(row=1, column=1, sticky="nw", pady=(0, 7))

        self._media_back = tk.Button(
            self._header,
            text="ALL MEDIA",
            command=self.show_hub,
            bg=ACTIVE,
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
        self._spotify_refresh_generation += 1
        self._spotify_refresh_in_flight = False
        self._cancel_spotify_refresh()
        self._spotify_presenter = None
        self._spotify_panel = None
        if self._spotify_video_controller is not None:
            self._spotify_video_controller.stop_video()
            self._spotify_video_controller = None
        if self._view_host is not None:
            for child in self._view_host.winfo_children():
                child.destroy()

    def _cancel_spotify_refresh(self) -> None:
        if self._spotify_refresh_job is None:
            return
        try:
            self.after_cancel(self._spotify_refresh_job)
        except tk.TclError:
            pass
        self._spotify_refresh_job = None

    def _refresh_spotify(self) -> None:
        presenter = self._spotify_presenter
        panel = self._spotify_panel
        if presenter is None or panel is None or self._closed or self._spotify_refresh_in_flight:
            return
        generation = self._spotify_refresh_generation
        self._spotify_refresh_in_flight = True
        threading.Thread(
            target=self._load_spotify_state,
            args=(presenter, generation),
            name="orcui-spotify-state",
            daemon=True,
        ).start()
        self._spotify_refresh_job = self.after(25, lambda: self._poll_spotify_state(generation))

    def _load_spotify_state(self, presenter: SpotifyMediaPresenter, generation: int) -> None:
        state = presenter.read_state()
        self._spotify_state_results.put((generation, state))

    def _poll_spotify_state(self, generation: int) -> None:
        self._spotify_refresh_job = None
        panel = self._spotify_panel
        if panel is None or self._closed or generation != self._spotify_refresh_generation:
            return
        while True:
            try:
                result_generation, state = self._spotify_state_results.get_nowait()
            except queue.Empty:
                self._spotify_refresh_job = self.after(25, lambda: self._poll_spotify_state(generation))
                return
            if result_generation == generation:
                break
        self._spotify_refresh_in_flight = False
        try:
            panel.set_media_state(state)
        except tk.TclError:
            return
        self._spotify_refresh_job = self.after(5000, self._refresh_spotify)

    def _dispatch_ui(self, callback: Callable[[], None]) -> None:
        self._ui_dispatch_queue.put(callback)

    def _poll_ui_dispatch(self) -> None:
        self._ui_dispatch_job = None
        if self._closed:
            return
        for _ in range(100):
            try:
                callback = self._ui_dispatch_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except (RuntimeError, tk.TclError):
                pass
        self._ui_dispatch_job = self.after(25, self._poll_ui_dispatch)

    def _media_card(
        self,
        parent: tk.Widget,
        glyph: str,
        title: str,
        category: str,
        subtitle: str,
        detail: str,
        action: str,
        accent: str,
        command: Callable[[], None],
    ) -> tk.Frame:
        card = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER, cursor="hand2")
        tk.Frame(card, bg=accent, height=6).pack(fill=tk.X)

        body = tk.Frame(card, bg=PANEL)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=(14, 12))

        top = tk.Frame(body, bg=PANEL)
        top.pack(fill=tk.X)

        glyph_box = tk.Frame(top, bg=accent, width=48, height=48)
        glyph_box.pack(side=tk.LEFT)
        glyph_box.pack_propagate(False)
        tk.Label(
            glyph_box,
            text=glyph,
            bg=accent,
            fg=BG,
            font=("Sans", 22, "bold"),
        ).pack(fill=tk.BOTH, expand=True)

        identity = tk.Frame(top, bg=PANEL)
        identity.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0))
        tk.Label(identity, text=title, bg=PANEL, fg=TEXT, font=("Sans", 16, "bold")).pack(anchor="w")
        tk.Label(identity, text=category, bg=PANEL, fg=accent, font=("Sans", 8, "bold")).pack(anchor="w", pady=(2, 0))

        tk.Label(
            body,
            text=subtitle,
            bg=PANEL,
            fg=TEXT,
            font=("Sans", 12, "bold"),
        ).pack(anchor="w", pady=(18, 5))
        tk.Label(
            body,
            text=detail,
            bg=PANEL,
            fg=MUTED,
            font=("Sans", 9),
            justify=tk.LEFT,
            wraplength=220,
        ).pack(anchor="w")

        button = tk.Button(
            body,
            text=f"{action}   ›",
            command=command,
            bg=accent,
            fg=BG,
            activebackground=accent,
            activeforeground=BG,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 9, "bold"),
            padx=12,
            pady=9,
            cursor="hand2",
        )
        button.pack(fill=tk.X, side=tk.BOTTOM, pady=(14, 0))

        self._bind_card(card, command)
        self._bind_hover(card, accent)
        return card

    @staticmethod
    def _bind_card(widget: tk.Widget, command: Callable[[], None]) -> None:
        widget.bind("<Button-1>", lambda _event: command())
        for child in widget.winfo_children():
            if isinstance(child, tk.Button):
                continue
            MediaPanel._bind_card(child, command)

    @staticmethod
    def _bind_hover(card: tk.Frame, accent: str) -> None:
        card.bind("<Enter>", lambda _event: card.configure(highlightbackground=accent, highlightthickness=2))
        card.bind("<Leave>", lambda _event: card.configure(highlightbackground=BORDER, highlightthickness=1))

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
