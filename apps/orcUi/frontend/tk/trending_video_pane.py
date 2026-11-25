# SPDX-License-Identifier: MIT
"""Embedded YouTube search inside the Radio Trending left pane."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from frontends.x11 import X11WindowEmbedder
from ui.media.trending_video import TrendingVideoSession
from ui.ui_widget import UiWidget


class TrendingVideoPane(tk.Frame, UiWidget):
    """Own a single browser embedding and its managed process lifecycle."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        session: TrendingVideoSession,
        on_back: Callable[[], None],
        window_class: str,
        background: str,
        foreground: str,
        on_error: Callable[[str], None],
    ) -> None:
        super().__init__(parent, bg=background)
        self._session = session
        self._on_error = on_error
        self._window_class = window_class
        self._embedder = X11WindowEmbedder()
        self._pending: str | None = None
        self._closed = False
        bar = tk.Frame(self, bg=background)
        bar.pack(fill=tk.X)
        tk.Button(
            bar,
            text="‹ BACK",
            command=on_back,
            bg=background,
            fg=foreground,
            relief=tk.FLAT,
            font=("Sans", 11, "bold"),
        ).pack(side=tk.LEFT)
        self._status = tk.Label(
            bar, text="Opening YouTube…", bg=background, fg=foreground, anchor="w"
        )
        self._status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._host = tk.Frame(self, bg=background)
        self._host.pack(fill=tk.BOTH, expand=True)
        self._host.bind("<Configure>", self._resize)
        self._pending = self.after(100, self._await_result)

    def _await_result(self) -> None:
        self._pending = None
        if self._closed:
            return
        target = self._session.poll_target()
        if target is None:
            self._pending = self.after(100, self._await_result)
            return
        self._launch(target)

    def _launch(self, target: str) -> None:
        self._pending = None
        if self._closed or not self._host.winfo_exists():
            return
        try:
            self._host.update_idletasks()
            width = max(1, self._host.winfo_width())
            height = max(1, self._host.winfo_height())
            if not self._session.play(
                target,
                (self._host.winfo_rootx(), self._host.winfo_rooty()),
                (width, height),
            ):
                raise RuntimeError("YouTube browser could not start")
            self._embedder.embed(
                0,
                int(self._host.winfo_id()),
                width,
                height,
                window_class=self._window_class,
                relax_size_hints=True,
            )
            self._status.configure(text="")
            self.after(900, self._maximize_player)
        except Exception as exc:
            self._session.close()
            self._status.configure(text="YouTube unavailable")
            self._on_error(str(exc))

    def _maximize_player(self) -> None:
        """Request YouTube theater mode without fullscreening the ORC window."""
        if self._closed or self._embedder.window_id is None:
            return
        self._session.theater(self._embedder.window_id)

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
        self._session.close()
        super().destroy()
