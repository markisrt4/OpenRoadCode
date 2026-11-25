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
        window.configure(bg=ui.surface, highlightthickness=2, highlightbackground=ui.text_muted)
        window.protocol("WM_DELETE_WINDOW", self.dismiss)
        window.overrideredirect(True)
        width = min(840, int(self._root.winfo_screenwidth() * 0.85))
        compact = self._root.winfo_screenheight() < 600
        height = 220 if compact else 300
        x = (self._root.winfo_screenwidth() - width) // 2
        y = (self._root.winfo_screenheight() - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.bind("<Escape>", lambda _event: self.dismiss())
        tk.Frame(window, bg=ui.accent_danger, height=6).pack(fill=tk.X)
        tk.Label(
            window,
            text=title or "ERROR",
            bg=ui.surface,
            fg=ui.accent_danger,
            font=("Sans", 20 if compact else 28, "bold"),
            anchor="w",
        ).pack(fill=tk.X, padx=24, pady=(18, 8))
        tk.Label(
            window,
            text=message,
            bg=ui.surface,
            fg=ui.text,
            wraplength=width - 56,
            justify=tk.LEFT,
            anchor="nw",
            font=("Sans", 16 if compact else 22),
        ).pack(fill=tk.BOTH, expand=True, padx=24)
        tk.Button(
            window,
            text="DISMISS",
            command=self.dismiss,
            bg=ui.control_background,
            fg=ui.control_text,
            relief=tk.FLAT,
            font=("Sans", 16 if compact else 20, "bold"),
            padx=24,
            pady=12,
        ).pack(pady=(6, 14))
        window.lift()

    def dismiss(self) -> None:
        window = self._window
        self._window = None
        if window is not None and window.winfo_exists():
            window.destroy()
