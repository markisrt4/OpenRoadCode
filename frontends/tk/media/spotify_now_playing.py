# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact Spotify now-playing summary for the ORC home screen."""

from __future__ import annotations

import io
import tkinter as tk
from collections.abc import Callable

from PIL import Image, ImageOps, ImageTk

from ui.media.spotify_presentation_if import SpotifyPresentationState, SpotifyVideoRequests, SpotifyRequestHandler
from ui.media import PlaybackState
from ui.theme import ThemeBundle
from ui.ui_widget import UiWidget

GREEN = "#1DB954"
ART_SIZE = 84


class SpotifyNowPlaying(tk.Frame, UiWidget):
    """Render shared Spotify state and cached artwork without network work in Tk."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        on_open: Callable[[], None],
        theme_bundle: Callable[[], ThemeBundle],
        online_allowed: Callable[[], bool] = lambda: True,
        on_playback_changed: Callable[[bool], None] | None = None,
    ) -> None:
        self._online_allowed = online_allowed
        self._on_playback_changed = on_playback_changed
        self._last_playing: bool | None = None
        self._theme_provider = theme_bundle
        self._theme = theme_bundle()
        ui = self._theme.ui
        super().__init__(parent, bg=ui.surface, cursor="hand2")
        self._on_open = on_open
        self._closed = False
        self._title = tk.StringVar(value="Spotify • YouTube • Netflix")
        self._artist = tk.StringVar(value="Media hub")
        self._status = tk.StringVar(value="")
        self._artwork_uri: str | None = None
        self._artwork_photo: ImageTk.PhotoImage | None = None
        self._artwork_payload: bytes | None = None
        self._body = tk.Frame(self, bg=ui.surface)
        self._body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(7, 4))
        self._body.grid_columnconfigure(1, weight=1)
        self._body.grid_rowconfigure(0, weight=1)

        self._art_host = tk.Frame(self._body, bg=ui.surface)
        self._art_host.grid(row=0, column=0, sticky="nw", padx=(0, 8))
        self._art_label = tk.Label(
            self._art_host, text="♫", fg=GREEN, bg=ui.control_active,
            font=("Sans", 23, "bold"), width=4, height=2, anchor="center",
        )
        self._art_label.pack()
        self._art_loading = tk.Label(
            self._art_host, text="", fg=ui.text_muted, bg=ui.surface,
            font=("Sans", 6, "bold"),
        )
        self._art_loading.pack(pady=(2, 0))

        self._text = tk.Frame(self._body, bg=ui.surface)
        self._text.grid(row=0, column=1, sticky="new")
        self._text.grid_columnconfigure(0, weight=1)
        self._title_label = tk.Label(
            self._text, textvariable=self._title, fg=ui.text, bg=ui.surface,
            font=("Sans", 12, "bold"), anchor="w", justify=tk.LEFT,
        )
        self._title_label.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        self._artist_label = tk.Label(
            self._text, textvariable=self._artist, fg=ui.text_muted, bg=ui.surface,
            font=("Sans", 9), anchor="w", justify=tk.LEFT,
        )
        self._artist_label.grid(row=1, column=0, sticky="ew")
        self._status_label = tk.Label(
            self._text, textvariable=self._status, fg=GREEN, bg=ui.surface,
            font=("Sans", 7, "bold"), anchor="w",
        )
        self._status_label.grid(row=2, column=0, sticky="ew", pady=(3, 0))

        self._progress = tk.Canvas(self, height=6, bg=ui.surface,
                                   highlightthickness=0, bd=0)
        self._progress.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 7))
        self._progress.pack_forget()
        self._progress_fraction: float | None = None
        self._progress.bind("<Configure>", lambda _event: self._paint_progress())
        self._bind_open(self)

    def destroy(self) -> None:
        self._closed = True
        super().destroy()

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        """Apply live shell colors while preserving Spotify brand accents."""
        self._theme = theme
        ui = theme.ui
        self.configure(bg=ui.surface)
        self._body.configure(bg=ui.surface)
        self._art_host.configure(bg=ui.surface)
        self._text.configure(bg=ui.surface)
        self._art_loading.configure(bg=ui.surface, fg=ui.text_muted)
        self._title_label.configure(bg=ui.surface, fg=ui.text)
        self._artist_label.configure(bg=ui.surface, fg=ui.text_muted)
        self._status_label.configure(bg=ui.surface, fg=GREEN)
        self._progress.configure(bg=ui.surface)
        if self._artwork_photo is None:
            self._art_label.configure(bg=ui.control_active, fg=GREEN)

    def _bind_open(self, widget: tk.Misc) -> None:
        widget.bind("<Button-1>", lambda _event: self._on_open())
        for child in widget.winfo_children():
            self._bind_open(child)

    def _paint_progress(self) -> None:
        self._progress.delete("all")
        width = self._progress.winfo_width()
        if width <= 1:
            return
        self._progress.create_rectangle(0, 0, width, 5, fill=self._theme.ui.border, outline="")
        if self._progress_fraction is not None:
            self._progress.create_rectangle(
                0, 0, width * self._progress_fraction, 5, fill=GREEN, outline="",
            )

    def set_spotify_request_handler(self, handler: SpotifyRequestHandler | None) -> None:
        """The home summary emits only its supplied navigation action."""

    def set_video_request_handler(self, handler: SpotifyVideoRequests | None) -> None:
        """Home summary has no video controls."""

    def set_spotify_state(self, presentation: SpotifyPresentationState) -> None:
        if self._closed:
            return
        current_theme = self._theme_provider()
        if current_theme != self._theme:
            self.set_theme_bundle(current_theme)
        state = presentation.media
        playing = presentation.online and state.playback is PlaybackState.PLAYING
        if playing != self._last_playing:
            self._last_playing = playing
            if self._on_playback_changed is not None:
                self._on_playback_changed(playing)
        self._progress_fraction = (
            max(0.0, min(1.0, state.position_s / state.duration_s))
            if state.position_s is not None and state.duration_s is not None
            and state.duration_s > 0 else None
        )
        if self._progress_fraction is None:
            self._progress.pack_forget()
        elif not self._progress.winfo_manager():
            self._progress.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 7))
        self._paint_progress()
        self.configure(cursor="hand2" if presentation.online else "arrow")
        if not presentation.online:
            self._title.set("Streaming media unavailable")
            self._artist.set("Offline mode")
            self._status.set("")
            self._show_artwork_placeholder()
        elif state.playback in (PlaybackState.PLAYING, PlaybackState.PAUSED) and state.title:
            self._title.set(state.title if len(state.title) <= 23 else state.title[:22] + "…")
            artist = state.artist or ""
            self._artist.set(artist if len(artist) <= 25 else artist[:24] + "…")
            self._status.set(
                "Spotify • Playing" if state.playback is PlaybackState.PLAYING
                else "Spotify • Paused"
            )
            self._art_loading.configure(text="LOADING" if presentation.artwork_loading else "")
            if presentation.artwork != self._artwork_payload:
                self._artwork_payload = presentation.artwork
                self._artwork_photo = None
                self._art_label.configure(image="", text="♫", width=4, height=2)
                if presentation.artwork:
                    try:
                        with Image.open(io.BytesIO(presentation.artwork)) as source:
                            image = ImageOps.fit(source, (ART_SIZE, ART_SIZE))
                            try:
                                self._artwork_photo = ImageTk.PhotoImage(image)
                            finally:
                                image.close()
                        self._art_label.configure(image=self._artwork_photo, text="", width=ART_SIZE, height=ART_SIZE)
                    except (OSError, ValueError):
                        pass
        else:
            self._title.set("Spotify • YouTube • Netflix")
            self._artist.set("Media hub")
            self._status.set("")
            self._show_artwork_placeholder()

    def _show_artwork_placeholder(self) -> None:
        self._artwork_payload = None
        self._artwork_photo = None
        self._art_loading.configure(text="")
        self._art_label.configure(image="", text="♫", width=4, height=2)
        self._art_label.configure(bg=self._theme.ui.control_active, fg=GREEN)
