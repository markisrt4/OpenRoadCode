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
ART_SIZE = 94


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
        self._requests: SpotifyRequestHandler | None = None
        self._playing = False
        self._title = tk.StringVar(value="Spotify • YouTube • Netflix")
        self._artist = tk.StringVar(value="Media hub")
        self._status = tk.StringVar(value="")
        self._artwork_uri: str | None = None
        self._artwork_photo: ImageTk.PhotoImage | None = None
        self._artwork_payload: bytes | None = None
        self._body = tk.Frame(self, bg=ui.surface)
        self._body.pack(fill=tk.BOTH, expand=True, padx=9, pady=(1, 1))
        self._body.grid_columnconfigure(1, weight=1)
        self._body.grid_rowconfigure(0, weight=1)

        self._art_host = tk.Frame(self._body, bg=ui.surface)
        self._art_host.grid(row=0, column=0, sticky="w", padx=(0, 8))
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
        self._text.grid(row=0, column=1, sticky="ew")
        self._text.grid_columnconfigure(0, weight=1)
        self._title_label = tk.Label(
            self._text, textvariable=self._title, fg=ui.text, bg=ui.surface,
            font=("Sans", 12, "bold"), anchor="w", justify=tk.LEFT,
            wraplength=128,
        )
        self._title_label.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        self._artist_label = tk.Label(
            self._text, textvariable=self._artist, fg=ui.text_muted, bg=ui.surface,
            font=("Sans", 9), anchor="w", justify=tk.LEFT,
            wraplength=128,
        )
        self._artist_label.grid(row=1, column=0, sticky="ew")
        self._provider = tk.Frame(self._text, bg=ui.surface)
        self._provider.grid(row=2, column=0, sticky="w", pady=(6, 0))
        self._spotify_icon = tk.Label(self._provider, text="◉", fg=GREEN, bg=ui.surface,
                                      font=("Sans", 12, "bold"))
        self._spotify_icon.pack(side=tk.LEFT, padx=(0, 4))
        self._status_label = tk.Label(
            self._provider, textvariable=self._status, fg=GREEN, bg=ui.surface,
            font=("Sans", 8, "bold"), anchor="w",
        )
        self._status_label.pack(side=tk.LEFT)
        self._provider.grid_remove()
        self._text.bind("<Configure>", self._resize_text_wrap)

        self._footer = tk.Frame(self, bg=ui.surface)
        self._footer.pack(side=tk.BOTTOM, fill=tk.X, padx=9, pady=(0, 3))
        self._footer_text = tk.Label(
            self._footer, text="OPEN MEDIA ›", bg=ui.surface,
            fg=ui.accent_primary, font=("Sans", 8, "bold"), anchor="w",
        )
        self._footer_text.pack_forget()
        self._controls = tk.Frame(self._footer, bg=ui.surface)
        self._controls.pack(side=tk.RIGHT)
        self._previous = tk.Button(self._controls, text="⏮", command=self._previous_track,
            font=("Sans", 13, "bold"), width=3, padx=2, pady=5, relief=tk.FLAT, bd=0,
            bg=ui.control_background, fg=ui.text, activebackground=ui.control_active)
        self._toggle = tk.Button(self._controls, text="▶", command=self._toggle_playback,
            font=("Sans", 12, "bold"), width=3, padx=1, pady=3, relief=tk.FLAT, bd=0,
            bg=GREEN, fg="#ffffff", activebackground=ui.control_active)
        self._next = tk.Button(self._controls, text="⏭", command=self._next_track,
            font=("Sans", 12, "bold"), width=3, padx=1, pady=3, relief=tk.FLAT, bd=0,
            bg=ui.control_background, fg=ui.text, activebackground=ui.control_active)
        for button in (self._previous, self._toggle, self._next):
            button.pack(side=tk.LEFT, padx=(2, 0))
        self._update_controls()
        self._progress = tk.Canvas(self, height=4, bg=ui.surface,
                                   highlightthickness=0, bd=0)
        self._progress.pack(side=tk.BOTTOM, fill=tk.X, expand=False, padx=10, pady=(0, 2))
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
        self._provider.configure(bg=ui.surface)
        self._spotify_icon.configure(bg=ui.surface, fg=GREEN)
        self._progress.configure(bg=ui.surface)
        self._footer.configure(bg=ui.surface)
        self._footer_text.configure(bg=ui.surface, fg=ui.accent_primary)
        self._controls.configure(bg=ui.surface)
        for button in (self._previous, self._next):
            button.configure(bg=ui.control_background, fg=ui.text,
                             activebackground=ui.control_active)
        self._toggle.configure(activebackground=ui.control_active)
        if self._artwork_photo is None:
            self._art_label.configure(bg=ui.control_active, fg=GREEN)

    def _bind_open(self, widget: tk.Misc) -> None:
        widget.bind("<Button-1>", lambda _event: self._on_open())
        for child in widget.winfo_children():
            if child is self._controls:
                continue
            self._bind_open(child)

    def _resize_text_wrap(self, event: tk.Event) -> None:
        available = max(64, event.width - 4)
        self._title_label.configure(wraplength=available)
        self._artist_label.configure(wraplength=available)

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

    def _update_controls(self) -> None:
        enabled = self._requests is not None and self._online_allowed()
        for button in (self._previous, self._toggle, self._next):
            button.configure(state=tk.NORMAL if enabled else tk.DISABLED)
        self._toggle.configure(text="Ⅱ" if self._playing else "▶")

    def _previous_track(self) -> None:
        if self._requests is not None:
            self._requests.request_previous_track()

    def _toggle_playback(self) -> None:
        if self._requests is not None:
            if self._playing:
                self._requests.request_pause()
            else:
                self._requests.request_play()

    def _next_track(self) -> None:
        if self._requests is not None:
            self._requests.request_next_track()

    def set_spotify_request_handler(self, handler: SpotifyRequestHandler | None) -> None:
        self._requests = handler
        self._update_controls()

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
        self._playing = playing
        self._update_controls()
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
            self._progress.pack(side=tk.BOTTOM, fill=tk.X, expand=False, padx=10, pady=(0, 2))
        self._paint_progress()
        self.configure(cursor="hand2" if presentation.online else "arrow")
        if not presentation.online:
            self._title.set("Streaming media unavailable")
            self._artist.set("Offline mode")
            self._status.set("")
            self._provider.grid_remove()
            self._show_artwork_placeholder()
        elif state.playback in (PlaybackState.PLAYING, PlaybackState.PAUSED) and state.title:
            self._title.set(state.title)
            artist = state.artist or ""
            self._artist.set(artist)
            self._status.set("Spotify · Playing" if playing else "Spotify · Paused")
            self._provider.grid()
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
