# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


class BrowserReturnOverlay:
    """Borderless return button displayed above a panel browser window."""

    def __init__(
        self,
        owner: tk.Misc,
        *,
        command: Callable[[], None],
        background: str,
        foreground: str,
        active_background: str,
    ) -> None:
        self._owner = owner
        self._command = command
        self._background = background
        self._foreground = foreground
        self._active_background = active_background
        self._window: tk.Toplevel | None = None

    def show(
        self,
        *,
        x: int,
        y: int,
        display: str | None = None,
    ) -> None:
        """Show the return control, optionally on another X display.

        @param x Horizontal screen coordinate.
        @param y Vertical screen coordinate.
        @param display Optional X display hosting the browser window.
        """
        self.hide()
        window = tk.Toplevel(self._owner, screen=display)
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        window.configure(bg=self._background)
        window.geometry(f"+{x}+{y}")

        tk.Button(
            window,
            text="‹  RETURN",
            command=self._command,
            bg=self._background,
            fg=self._foreground,
            activebackground=self._active_background,
            activeforeground=self._foreground,
            font=("DejaVu Sans", 12, "bold"),
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            padx=14,
            pady=8,
        ).pack()
        window.lift()
        self._window = window

    def hide(self) -> None:
        if self._window is not None:
            self._window.destroy()
            self._window = None
