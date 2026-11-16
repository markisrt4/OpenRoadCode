# SPDX-License-Identifier: MIT
"""Canvas-based, touch-sized automotive radio control."""
from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


class AutomotiveRadioButton(tk.Canvas):
    """Rounded radio tile with explicit selected, hover, and disabled states."""

    def __init__(self, parent: tk.Misc, *, text: str, command: Callable[[], None],
                 selected: bool = False, height: int = 52,
                 background: str = "#0c1925", accent: str = "#168ddd",
                 foreground: str = "#f0f7ff", border: str = "#29445b",
                 font_size: int = 11) -> None:
        super().__init__(parent, height=height, bg=background,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._text = text
        self._command = command
        self._selected = selected
        self._hover = False
        self._background = background
        self._accent = accent
        self._foreground = foreground
        self._border = border
        self._font_size = font_size
        self.bind("<Configure>", lambda _event: self._paint())
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonPress-1>", lambda _event: self.focus_set())
        self.bind("<ButtonRelease-1>", self._activate)
        self.bind("<Return>", self._activate)
        self.bind("<space>", self._activate)
        self.configure(takefocus=1)

    def set_text(self, text: str) -> None:
        """Update the label of this canvas-backed control."""
        if self._text != text:
            self._text = text
            self._paint()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._paint()

    def set_palette(self, *, background: str, accent: str,
                    foreground: str, border: str) -> None:
        self._background, self._accent = background, accent
        self._foreground, self._border = foreground, border
        self.configure(bg=background)
        self._paint()

    def _enter(self, _event: tk.Event) -> None:
        self._hover = True
        self._paint()

    def _leave(self, _event: tk.Event) -> None:
        self._hover = False
        self._paint()

    def _activate(self, _event: tk.Event) -> None:
        if self._command:
            self._command()

    def _paint(self) -> None:
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 12 or h < 12:
            return
        r = min(12, h // 4)
        fill = self._accent if self._selected else self._background
        edge = self._accent if self._hover and not self._selected else self._background
        # Solid rounded tile: avoid overlapping oval/rectangle seams and heavy outlines.
        self.create_rectangle(r, 2, w-r, h-2, fill=fill, outline="")
        self.create_rectangle(2, r, w-2, h-r, fill=fill, outline="")
        for x in (r+2, w-r-2):
            for y in (r+2, h-r-2):
                self.create_oval(x-r, y-r, x+r, y+r, fill=fill, outline="")
        if self._hover and not self._selected:
            self.create_line(10, h-3, w-10, h-3, fill=edge, width=2)
        self.create_text(w/2, h/2, text=self._text, fill=self._foreground,
                         font=("Sans", self._font_size, "bold"), width=max(20, w-18))
