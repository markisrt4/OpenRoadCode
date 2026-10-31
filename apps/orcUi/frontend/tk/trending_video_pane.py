# SPDX-License-Identifier: MIT
"""Embedded YouTube search inside the Radio Trending left pane."""

from __future__ import annotations

import os
import subprocess
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from controllers.media.youtube_search_resolver import first_video_url
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
        self._resolver = ThreadPoolExecutor(max_workers=1, thread_name_prefix="trending-youtube")
        self._future = self._resolver.submit(first_video_url, query)
        self._resolved_target = query
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
        self._pending = self.after(100, self._await_result)

    def _await_result(self) -> None:
        self._pending = None
        if self._closed:
            return
        if not self._future.done():
            self._pending = self.after(100, self._await_result)
            return
        try:
            self._resolved_target = self._future.result()
        except Exception:
            self._resolved_target = self._query
        self._launch()

    def _launch(self) -> None:
        self._pending = None
        if self._closed or not self._host.winfo_exists():
            return
        try:
            self._host.update_idletasks()
            width = max(1, self._host.winfo_width())
            height = max(1, self._host.winfo_height())
            if not self._play(
                self._resolved_target, display=os.environ.get("DISPLAY", ":1"),
                window_position=(self._host.winfo_rootx(), self._host.winfo_rooty()),
                window_size=(width, height),
            ):
                raise RuntimeError("YouTube browser could not start")
            self._embedder.embed(0, int(self._host.winfo_id()), width, height,
                                 window_class=self._window_class)
            self._status.configure(text="YOUTUBE")
            self.after(900, self._maximize_player)
        except Exception as exc:
            self._status.configure(text=f"YouTube unavailable: {exc}")

    def _maximize_player(self) -> None:
        """Request YouTube theater mode without fullscreening the ORC window."""
        if self._closed or self._embedder.window_id is None:
            return
        try:
            subprocess.run(
                ["xdotool", "key", "--window", str(self._embedder.window_id), "t"],
                check=False, timeout=1, capture_output=True,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass

    def _resize(self, event: tk.Event) -> None:
        if self._embedder.window_id is not None:
            self._embedder.resize(max(1, event.width), max(1, event.height))

    def destroy(self) -> None:
        self._closed = True
        if self._pending is not None:
            self.after_cancel(self._pending)
            self._pending = None
        # The embedded child belongs to the managed Chromium process.
        # Reparenting it during shutdown races Chromium's own window destruction
        # and produces BadWindow errors on Termux X11. Stop the process instead.
        self._embedder.clear()
        self._resolver.shutdown(wait=False, cancel_futures=True)
        from threading import Thread
        Thread(target=self._stop, name="trending-browser-close", daemon=True).start()
        super().destroy()
