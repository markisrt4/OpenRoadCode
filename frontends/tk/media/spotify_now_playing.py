# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact Spotify now-playing summary for the ORC home screen."""

from __future__ import annotations

import io
from functools import partial
import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable

from PIL import Image, ImageOps, ImageTk

from ui.media.spotify_presentation_if import SpotifyPresentationState, SpotifyVideoRequests, SpotifyRequestHandler
from ui.media import PlaybackState, MediaAvailability
from ui.theme import ThemeBundle
from ui.ui_widget import UiWidget
from .metadata_text import fit_metadata_text
from .home_spectrum_strip import HomeSpectrumStrip
from ui.music_visualizer.home_spectrum_ui_if import HomeSpectrumFeedIf

GREEN = "#1DB954"
ART_SIZE = 48


class SpotifyNowPlaying(tk.Frame, UiWidget):
    """Render shared Spotify state and cached artwork without network work in Tk."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        on_open: Callable[[], None],
        on_open_media: Callable[[], None] | None = None,
        spectrum_feed: HomeSpectrumFeedIf | None = None,
        on_open_visualizer: Callable[[], None] | None = None,
        theme_bundle: Callable[[], ThemeBundle],
        online_allowed: Callable[[], bool] = lambda: True,
    ) -> None:
        self._online_allowed = online_allowed
        self._theme_provider = theme_bundle
        self._theme = theme_bundle()
        ui = self._theme.ui
        super().__init__(parent, bg=ui.surface, cursor="hand2")
        self._on_open = on_open
        self._closed = False
        self._handler: SpotifyRequestHandler | None = None
        self._playing = False
        self._can_control = False
        self._title = tk.StringVar(value="Music & video")
        self._artist = tk.StringVar(value="Open Media to browse")
        self._status = tk.StringVar(value="")
        self._title_text = "Music & video"
        self._artist_text = "Open Media to browse"
        self._title_font = tkfont.Font(root=self, family="Sans", size=14, weight="bold")
        self._artist_font = tkfont.Font(root=self, family="Sans", size=10)
        self._artwork_uri: str | None = None
        self._artwork_photo: ImageTk.PhotoImage | None = None
        self._artwork_payload: bytes | None = None
        self._body = tk.Frame(self, bg=ui.surface)
        self._body.grid_columnconfigure(1, weight=1)
        self._body.grid_rowconfigure(0, weight=1)

        self._art_host = tk.Frame(self._body, bg=ui.surface)
        self._art_host.grid(row=0, column=0, sticky="nw", padx=(0, 9))
        self._art_label = tk.Label(
            self._art_host, text="♫", fg=GREEN, bg=ui.control_active,
            font=("Sans", 20, "bold"), width=3, height=1, anchor="center",
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
            font=self._title_font, width=1, height=2, anchor="nw", justify=tk.LEFT,
        )
        self._title_label.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        self._artist_label = tk.Label(
            self._text, textvariable=self._artist, fg=ui.text_muted, bg=ui.surface,
            font=self._artist_font, width=1, height=1, anchor="w", justify=tk.LEFT,
        )
        self._artist_label.grid(row=1, column=0, sticky="ew")
        self._status_label = tk.Label(
            self._text, textvariable=self._status, fg=GREEN, bg=ui.surface,
            font=("Sans", 7, "bold"), anchor="w",
        )
        # Spectrum status replaces the small Spotify status line so the title,
        # artist, spectrum and transport still fit the fixed Home card height.
        if spectrum_feed is None:
            self._status_label.grid(row=2, column=0, sticky="ew", pady=(3, 0))

        self._bind_open(self)
        self._spectrum = (HomeSpectrumStrip(self._body, feed=spectrum_feed,
            background=ui.surface, on_open=on_open_visualizer or on_open)
            if spectrum_feed is not None else None)
        if self._spectrum is not None:
            self._spectrum.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 0))
        self._text.bind("<Configure>", lambda _event: self._render_metadata())
        controls = self._controls = tk.Frame(self, bg=ui.surface)
        controls.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 6))
        self._transport: list[tk.Button] = []
        for column, (label, action) in enumerate((("◀◀", "previous"), ("▶", "play"), ("▶▶", "next"))):
            controls.grid_columnconfigure(column, weight=1, uniform="home-playback")
            button = tk.Button(controls, text=label, command=partial(self._request_transport, action),
                bg=ui.control_background, fg=ui.control_text, activebackground=ui.control_active,
                activeforeground=ui.text, disabledforeground=ui.text_muted,
                font=("Sans", 16, "bold"), pady=10, relief=tk.RAISED, bd=2,
                highlightthickness=0, state=tk.DISABLED)
            button.grid(row=0, column=column, sticky="ew", padx=2)
            self._transport.append(button)
        self._media_button = tk.Button(controls, text="MEDIA  ›", command=on_open_media or on_open,
            bg=ui.surface, fg=ui.accent_primary, activebackground=ui.control_active,
            activeforeground=ui.text, font=("Sans", 10, "bold"), pady=7,
            relief=tk.FLAT, bd=0, highlightthickness=0)
        self._media_button.grid(row=0, column=3, sticky="nsew", padx=(4, 0))
        # Reserve the transport row before filling the remaining space with metadata.
        self._body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 4))

    def destroy(self) -> None:
        self._closed = True
        self._handler = None
        super().destroy()

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        """Apply live shell colors while preserving Spotify brand accents."""
        self._theme = theme
        ui = theme.ui
        if self._spectrum is not None:
            self._spectrum.set_background(ui.surface)
        self.configure(bg=ui.surface)
        self._body.configure(bg=ui.surface)
        self._controls.configure(bg=ui.surface)
        for button in self._transport:
            button.configure(bg=ui.control_background, fg=ui.control_text,
                activebackground=ui.control_active, activeforeground=ui.text,
                disabledforeground=ui.text_muted)
        self._media_button.configure(bg=ui.surface, fg=ui.accent_primary,
            activebackground=ui.control_active, activeforeground=ui.text)
        self._art_host.configure(bg=ui.surface)
        self._text.configure(bg=ui.surface)
        self._art_loading.configure(bg=ui.surface, fg=ui.text_muted)
        self._title_label.configure(bg=ui.surface, fg=ui.text)
        self._artist_label.configure(bg=ui.surface, fg=ui.text_muted)
        self._status_label.configure(bg=ui.surface, fg=GREEN)
        if self._artwork_photo is None:
            self._art_label.configure(bg=ui.control_active, fg=GREEN)

    def _bind_open(self, widget: tk.Misc) -> None:
        widget.bind("<Button-1>", lambda _event: self._on_open())
        for child in widget.winfo_children():
            self._bind_open(child)

    def set_spotify_request_handler(self, handler: SpotifyRequestHandler | None) -> None:
        """Bind or retire the active Home playback requests."""
        self._handler = handler
        self._paint_transport()

    def _paint_transport(self) -> None:
        if self._closed:
            return
        enabled = self._handler is not None and self._can_control
        for button in self._transport:
            button.configure(state=tk.NORMAL if enabled else tk.DISABLED)
        self._transport[1].configure(text="Ⅱ" if self._playing else "▶")

    def _request_transport(self, action: str) -> None:
        handler = self._handler
        if self._closed or handler is None or not self._can_control:
            return
        if action == "previous":
            handler.request_previous_track()
        elif action == "next":
            handler.request_next_track()
        elif self._playing:
            handler.request_pause()
        else:
            handler.request_play()

    def set_video_request_handler(self, handler: SpotifyVideoRequests | None) -> None:
        """Home summary has no video controls."""

    def set_spotify_state(self, presentation: SpotifyPresentationState) -> None:
        if self._closed:
            return
        current_theme = self._theme_provider()
        if current_theme != self._theme:
            self.set_theme_bundle(current_theme)
        state = presentation.media
        self._playing = state.playback is PlaybackState.PLAYING
        self._can_control = presentation.online and state.availability is MediaAvailability.AVAILABLE
        self._paint_transport()
        self.configure(cursor="hand2" if presentation.online else "arrow")
        if not presentation.online:
            self._title_label.configure(height=2, anchor="nw")
            self._set_metadata("Streaming media unavailable", "Offline mode")
            self._status.set("")
            self._show_artwork_placeholder()
        elif state.title:
            self._title_label.configure(height=2, anchor="nw")
            self._set_metadata(state.title, state.artist or "")
            self._status.set("Spotify • Playing" if self._playing else "Spotify • Paused"
                             if state.playback is PlaybackState.PAUSED else "Spotify • Ready")
            self._art_loading.configure(text="LOADING" if presentation.artwork_loading else "")
            if presentation.artwork != self._artwork_payload:
                self._artwork_payload = presentation.artwork
                self._artwork_photo = None
                self._art_label.configure(image="", text="♫", width=3, height=1)
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
            self._title_label.configure(height=1, anchor="w")
            self._set_metadata("Music & video", "Open Media to browse")
            self._status.set("")
            self._show_artwork_placeholder()

    def _set_metadata(self, title: str, artist: str) -> None:
        self._title_text, self._artist_text = title, artist
        self._render_metadata()

    def _render_metadata(self) -> None:
        width = max(1, self._text.winfo_width() - 4)
        if width <= 4:
            return
        self._title.set(fit_metadata_text(self._title_text, width, self._title_font.measure,
                                        lines=int(self._title_label.cget("height"))))
        self._artist.set(fit_metadata_text(self._artist_text, width, self._artist_font.measure, lines=1))

    def _show_artwork_placeholder(self) -> None:
        self._artwork_payload = None
        self._artwork_photo = None
        self._art_loading.configure(text="")
        self._art_label.configure(image="", text="♫", width=3, height=1)
        self._art_label.configure(bg=self._theme.ui.control_active, fg=GREEN)
