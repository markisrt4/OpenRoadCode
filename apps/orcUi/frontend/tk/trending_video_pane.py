# SPDX-License-Identifier: MIT
"""Embedded YouTube search inside the Radio Trending left pane."""

from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable

from frontends.x11 import X11WindowEmbedder


class TrendingVideoPane(tk.Frame):
    """Own a single browser embedding and its managed process lifecycle."""

    def __init__(self, parent: tk.Misc, *, query: str,
                 play: Callable[..., bool], stop: Callable[[], None],
                 on_back: Callable[[], None], window_class: str,
                 background: str, foreground: str) -> None:
        super().__init__(parent, bg=background)
        self._play = play
        self._stop = stop
        self._query = query
        self._window_class = window_class
        self._embedder = X11WindowEmbedder()
        self._pending: str | None = None
        self._closed = False
        bar = tk.Frame(self, bg=background)
        bar.pack(fill=tk.X)
        tk.Button(bar, text="‹ BACK TO FM", command=on_back,
                  bg=background, fg=foreground, relief=tk.FLAT,
                  font=("Sans", 11, "bold")).pack(side=tk.LEFT)
        self._status = tk.Label(bar, text="Opening YouTube…", bg=background,
                                fg=foreground, anchor="w")
        self._status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._host = tk.Frame(self, bg=background)
        self._host.pack(fill=tk.BOTH, expand=True)
        self._host.bind("<Configure>", self._resize)
        self._pending = self.after(50, self._launch)

    def _launch(self) -> None:
        self._pending = None
        if self._closed or not self._host.winfo_exists():
            return
        try:
            self._host.update_idletasks()
            width = max(1, self._host.winfo_width())
            height = max(1, self._host.winfo_height())
            if not self._play(
                self._query, display=os.environ.get("DISPLAY", ":1"),
                window_position=(self._host.winfo_rootx(), self._host.winfo_rooty()),
                window_size=(width, height),
            ):
                raise RuntimeError("YouTube browser could not start")
            self._embedder.embed(0, int(self._host.winfo_id()), width, height,
                                 window_class=self._window_class)
            self._status.configure(text="YOUTUBE")
        except Exception as exc:
            self._status.configure(text=f"YouTube unavailable: {exc}")

    def _resize(self, event: tk.Event) -> None:
        if self._embedder.window_id is not None:
            self._embedder.resize(max(1, event.width), max(1, event.height))

    def destroy(self) -> None:
        self._closed = True
        if self._pending is not None:
            self.after_cancel(self._pending)
            self._pending = None
        if self._embedder.window_id is not None:
            try:
                self._embedder.detach(int(self.winfo_toplevel().winfo_id()))
            except (RuntimeError, tk.TclError):
                self._embedder.clear()
        self._stop()
        super().destroy()
