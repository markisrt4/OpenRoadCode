# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact Spotify now-playing summary for the ORC home screen."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

from PIL import ImageTk

from apps.orcUi.spotify_state_service import SpotifyStateService
from apps.orcUi.theme_runtime import theme_bundle
from controllers.image import ImageCache
from ui.media import PlaybackState
from ui.theme import ThemeMode

GREEN = "#1DB954"
ART_SIZE = 64


class SpotifyNowPlaying(tk.Frame):
    """Render shared Spotify state and cached artwork without network work in Tk."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        service: SpotifyStateService,
        on_open: Callable[[], None],
    ) -> None:
        ui = theme_bundle(ThemeMode.DARK).ui
        super().__init__(parent, bg=ui.surface, cursor="hand2")
        self._service = service
        self._on_open = on_open
        self._closed = False
        self._title = tk.StringVar(value="Spotify • YouTube • Netflix")
        self._artist = tk.StringVar(value="Media hub")
        self._status = tk.StringVar(value="")
        self._artwork_uri: str | None = None
        self._artwork_photo: ImageTk.PhotoImage | None = None
        self._art_results: queue.SimpleQueue[tuple[str, object | None]] = queue.SimpleQueue()
        cache_dir = Path.home() / ".cache" / "openroadcode" / "spotify-artwork"
        self._image_cache = ImageCache(max_entries=16, cache_directory=cache_dir)

        body = tk.Frame(self, bg=ui.surface)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(7, 8))
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        art_host = tk.Frame(body, bg=ui.surface)
        art_host.grid(row=0, column=0, sticky="nw", padx=(0, 9))
        self._art_label = tk.Label(
            art_host,
            text="♫",
            fg=GREEN,
            bg=ui.control_active,
            font=("Sans", 20, "bold"),
            width=4,
            height=2,
            anchor="center",
        )
        self._art_label.pack()
        self._art_loading = tk.Label(
            art_host,
            text="",
            fg=ui.text_muted,
            bg=ui.surface,
            font=("Sans", 6, "bold"),
        )
        self._art_loading.pack(pady=(2, 0))

        text = tk.Frame(body, bg=ui.surface)
        text.grid(row=0, column=1, sticky="new")
        text.grid_columnconfigure(0, weight=1)
        tk.Label(text, textvariable=self._title, fg=ui.text, bg=ui.surface, font=("Sans", 11, "bold"), anchor="w", justify=tk.LEFT).grid(row=0, column=0, sticky="ew", pady=(0, 2))
        tk.Label(text, textvariable=self._artist, fg=ui.text_muted, bg=ui.surface, font=("Sans", 8), anchor="w", justify=tk.LEFT).grid(row=1, column=0, sticky="ew")
        tk.Label(text, textvariable=self._status, fg=GREEN, bg=ui.surface, font=("Sans", 7, "bold"), anchor="w").grid(row=2, column=0, sticky="ew", pady=(3, 0))

        self._bind_open(self)
        self._refresh()

    def destroy(self) -> None:
        self._closed = True
        super().destroy()

    def _bind_open(self, widget: tk.Widget) -> None:
        widget.bind("<Button-1>", lambda _event: self._on_open())
        for child in widget.winfo_children():
            self._bind_open(child)

    def _refresh(self) -> None:
        if self._closed:
            return
        self._apply_artwork_result()
        state = self._service.latest_state()
        if state.playback is PlaybackState.PLAYING and state.title:
            self._title.set(state.title)
            self._artist.set(state.artist or "")
            self._status.set("Spotify • Playing")
            if state.artwork_uri and state.artwork_uri != self._artwork_uri:
                self._load_artwork(state.artwork_uri)
        else:
            self._title.set("Spotify • YouTube • Netflix")
            self._artist.set("Media hub")
            self._status.set("")
            self._show_artwork_placeholder()
        self.after(500, self._refresh)

    def _load_artwork(self, uri: str) -> None:
        self._artwork_uri = uri
        self._artwork_photo = None
        self._art_label.configure(image="", text="♫", width=4, height=2)
        self._art_loading.configure(text="LOADING")

        def worker() -> None:
            try:
                image = self._image_cache.get(uri, width=ART_SIZE, height=ART_SIZE)
            except Exception:
                image = None
            self._art_results.put((uri, image))

        threading.Thread(target=worker, name="orcui-home-artwork", daemon=True).start()

    def _apply_artwork_result(self) -> None:
        while True:
            try:
                uri, image = self._art_results.get_nowait()
            except queue.Empty:
                return
            if uri != self._artwork_uri:
                continue
            self._art_loading.configure(text="")
            if image is None:
                continue
            self._artwork_photo = ImageTk.PhotoImage(image)
            self._art_label.configure(image=self._artwork_photo, text="", width=ART_SIZE, height=ART_SIZE)

    def _show_artwork_placeholder(self) -> None:
        self._artwork_uri = None
        self._artwork_photo = None
        self._art_loading.configure(text="")
        self._art_label.configure(image="", text="♫", width=4, height=2)
