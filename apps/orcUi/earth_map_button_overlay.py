# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Top-level MAP button kept above the embedded Google Earth X11 window."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


class EarthMapButtonOverlay:
    """Float the renderer-return button over Earth without consuming layout space."""

    _WIDTH = 112
    _HEIGHT = 36
    _MARGIN = 10

    def __init__(self, owner: tk.Misc, anchor: tk.Misc, on_map: Callable[[], None]) -> None:
        self._anchor = anchor
        self._window = tk.Toplevel(owner)
        self._window.withdraw()
        self._window.overrideredirect(True)
        self._window.configure(bg="#05090d")
        try:
            self._window.attributes("-topmost", True)
        except tk.TclError:
            pass

        button = tk.Button(
            self._window,
            text="▣  MAP",
            command=on_map,
            bg="#84ce1f",
            fg="#05090d",
            activebackground="#9ee63a",
            activeforeground="#05090d",
            relief=tk.FLAT,
            font=("Sans", 9, "bold"),
            borderwidth=0,
        )
        button.pack(fill=tk.BOTH, expand=True)

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
            x = self._anchor.winfo_rootx() + max(
                0, self._anchor.winfo_width() - self._WIDTH - self._MARGIN
            )
            y = self._anchor.winfo_rooty() + self._MARGIN
            self._window.geometry(f"{self._WIDTH}x{self._HEIGHT}+{x}+{y}")
            self._window.lift()
        except tk.TclError:
            pass
