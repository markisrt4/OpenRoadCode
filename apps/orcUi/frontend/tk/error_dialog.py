# SPDX-License-Identifier: MIT
"""Application-owned error dialog independent of embedded native surfaces."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


class ErrorDialog:
    """Display a single non-blocking, dismissible error window.

    This is a separate Tk toplevel rather than a label or canvas item inside
    an embedded native receiver or browser. Call only from the Tk UI thread.
    """

    def __init__(self, root: tk.Misc, theme: Callable[[], object]) -> None:
        self._root = root
        self._theme = theme
        self._window: tk.Toplevel | None = None

    def show(self, title: str, message: str) -> None:
        if self._window is not None and self._window.winfo_exists():
            self._window.destroy()
        ui = self._theme().ui
        window = tk.Toplevel(self._root)
        self._window = window
        window.title(title or "OpenRoadCode error")
        window.transient(self._root)
        window.resizable(False, False)
        window.configure(bg=ui.background)
        window.protocol("WM_DELETE_WINDOW", self.dismiss)
        window.geometry("440x180")
        tk.Label(
            window,
            text=title or "ERROR",
            bg=ui.background,
            fg=ui.accent_danger,
            font=("Sans", 14, "bold"),
            anchor="w",
        ).pack(fill=tk.X, padx=16, pady=(14, 6))
        tk.Label(
            window,
            text=message,
            bg=ui.background,
            fg=ui.text,
            wraplength=400,
            justify=tk.LEFT,
            anchor="nw",
            font=("Sans", 11),
        ).pack(fill=tk.BOTH, expand=True, padx=16)
        tk.Button(
            window,
            text="DISMISS",
            command=self.dismiss,
            bg=ui.control_background,
            fg=ui.control_text,
            relief=tk.FLAT,
        ).pack(pady=(6, 14))
        window.lift()

    def dismiss(self) -> None:
        window = self._window
        self._window = None
        if window is not None and window.winfo_exists():
            window.destroy()
