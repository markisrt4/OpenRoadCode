# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact Spotify now-playing summary for the ORC home screen."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable

from apps.common.spotify_controller_factory import create_spotify_controller
from apps.orcUi.orc_theme import DARK

PANEL = DARK["panel"]
TEXT = DARK["text"]
MUTED = DARK["muted"]
GREEN = "#84ce1f"


class SpotifyNowPlaying(tk.Frame):
    """Poll Spotify off the Tk thread and show the active track when playing."""

    def __init__(self, parent: tk.Widget, *, on_open: Callable[[], None]) -> None:
        super().__init__(parent, bg=PANEL, cursor="hand2")
        self._on_open = on_open
        self._controller = create_spotify_controller()
        self._closed = False
        self._generation = 0
        self._results: queue.SimpleQueue[tuple[int, tuple[bool, str, str]]] = queue.SimpleQueue()
        self._title = tk.StringVar(value="Spotify • YouTube • Netflix")
        self._artist = tk.StringVar(value="Media hub")
        self._status = tk.StringVar(value="")

        tk.Label(self, textvariable=self._title, fg=TEXT, bg=PANEL, font=("Sans", 14, "bold"), anchor="w").pack(fill=tk.X, padx=16, pady=(12, 1))
        tk.Label(self, textvariable=self._artist, fg=MUTED, bg=PANEL, font=("Sans", 9), anchor="w").pack(fill=tk.X, padx=16)
        tk.Label(self, textvariable=self._status, fg=GREEN, bg=PANEL, font=("Sans", 8, "bold"), anchor="w").pack(fill=tk.X, padx=16, pady=(2, 4))
        self._bind_open(self)
        self._refresh()

    def destroy(self) -> None:
        self._closed = True
        self._generation += 1
        super().destroy()

    def _bind_open(self, widget: tk.Widget) -> None:
        widget.bind("<Button-1>", lambda _event: self._on_open())
        for child in widget.winfo_children():
            self._bind_open(child)

    def _refresh(self) -> None:
        if self._closed:
            return
        self._generation += 1
        generation = self._generation
        threading.Thread(target=self._load, args=(generation,), name="orcui-home-spotify", daemon=True).start()
        self.after(25, lambda: self._poll(generation))

    def _load(self, generation: int) -> None:
        try:
            state = self._controller.current_state()
            result = (
                bool(state.is_available and state.is_playing and state.track_name),
                state.track_name or "",
                state.artist_name or "",
            )
        except Exception:
            result = (False, "", "")
        self._results.put((generation, result))

    def _poll(self, generation: int) -> None:
        if self._closed or generation != self._generation:
            return
        try:
            result_generation, result = self._results.get_nowait()
        except queue.Empty:
            self.after(25, lambda: self._poll(generation))
            return
        if result_generation != generation:
            self.after(25, lambda: self._poll(generation))
            return
        self._apply(result)
        self.after(5000, self._refresh)

    def _apply(self, result: tuple[bool, str, str]) -> None:
        playing, title, artist = result
        if playing:
            self._title.set(f"♫  {title}")
            self._artist.set(artist)
            self._status.set("Spotify • Playing")
        else:
            self._title.set("Spotify • YouTube • Netflix")
            self._artist.set("Media hub")
            self._status.set("")
