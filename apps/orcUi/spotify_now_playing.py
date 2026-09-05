# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact Spotify now-playing summary for the ORC home screen."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from apps.orcUi.orc_theme import DARK
from apps.orcUi.spotify_state_service import SpotifyStateService
from ui.media import PlaybackState

PANEL = DARK["panel"]
TEXT = DARK["text"]
MUTED = DARK["muted"]
GREEN = "#84ce1f"


class SpotifyNowPlaying(tk.Frame):
    """Render the shared Spotify state without doing network work in Tk."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        service: SpotifyStateService,
        on_open: Callable[[], None],
    ) -> None:
        super().__init__(parent, bg=PANEL, cursor="hand2")
        self._service = service
        self._on_open = on_open
        self._closed = False
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
        super().destroy()

    def _bind_open(self, widget: tk.Widget) -> None:
        widget.bind("<Button-1>", lambda _event: self._on_open())
        for child in widget.winfo_children():
            self._bind_open(child)

    def _refresh(self) -> None:
        if self._closed:
            return
        state = self._service.latest_state()
        if state.playback is PlaybackState.PLAYING and state.title:
            self._title.set(f"♫  {state.title}")
            self._artist.set(state.artist or "")
            self._status.set("Spotify • Playing")
        else:
            self._title.set("Spotify • YouTube • Netflix")
            self._artist.set("Media hub")
            self._status.set("")
        self.after(1000, self._refresh)
