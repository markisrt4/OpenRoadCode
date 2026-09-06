# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Top-level navigation controls kept above an embedded Google Earth window."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


class EarthControlsOverlay:
    """Host Earth controls in their own X11 top-level so Chromium cannot steal input."""

    def __init__(
        self,
        owner: tk.Misc,
        anchor: tk.Misc,
        *,
        background: str,
        text_color: str,
        follow_color: str,
        on_follow: Callable[[], None],
        on_zoom_in: Callable[[], None],
        on_zoom_out: Callable[[], None],
        on_north_up: Callable[[], None],
        on_recenter: Callable[[], None],
    ) -> None:
        self._anchor = anchor
        self._background = background
        self._text_color = text_color
        self._follow_color = follow_color
        self._window = tk.Toplevel(owner)
        self._window.withdraw()
        self._window.overrideredirect(True)
        self._window.configure(bg=background)
        try:
            self._window.attributes("-topmost", True)
        except tk.TclError:
            pass

        self._follow_button = self._button("F", on_follow, follow_color)
        self._follow_button.pack(fill=tk.X, padx=5, pady=7)
        for text, command in (
            ("+", on_zoom_in),
            ("−", on_zoom_out),
            ("N", on_north_up),
            ("◎", on_recenter),
        ):
            self._button(text, command, text_color).pack(fill=tk.X, padx=5, pady=3)

    def _button(self, text: str, command: Callable[[], None], foreground: str) -> tk.Button:
        return tk.Button(
            self._window,
            text=text,
            command=command,
            bg=self._background,
            fg=foreground,
            relief=tk.FLAT,
            font=("Sans", 11, "bold"),
        )

    def show(self) -> None:
        self.reposition()
        self._window.deiconify()
        self._window.lift()

    def hide(self) -> None:
        self._window.withdraw()

    def destroy(self) -> None:
        try:
            self._window.destroy()
        except tk.TclError:
            pass

    def reposition(self) -> None:
        try:
            self._anchor.update_idletasks()
            width = max(1, self._anchor.winfo_width())
            height = max(1, self._anchor.winfo_height())
            x = self._anchor.winfo_rootx()
            y = self._anchor.winfo_rooty()
            self._window.geometry(f"{width}x{height}+{x}+{y}")
            self._window.lift()
        except tk.TclError:
            pass

    def set_follow_enabled(self, enabled: bool) -> None:
        self._follow_button.configure(
            text="F" if enabled else "F̸",
            fg=self._follow_color if enabled else self._text_color,
        )
