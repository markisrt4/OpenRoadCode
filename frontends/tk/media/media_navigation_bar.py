# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared navigation for integrated media screens."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.theme import ThemeBundle


class MediaNavigationBar(tk.Frame):
    """Return to the media hub or Home without duplicating provider controls."""

    def __init__(
        self, parent: tk.Misc, *, theme_bundle: Callable[[], ThemeBundle],
        active: str, show_media: Callable[[], None], show_home: Callable[[], None],
        show_spotify: Callable[[], None], show_youtube: Callable[[], None],
        show_netflix: Callable[[], None],
    ) -> None:
        ui = theme_bundle().ui
        super().__init__(parent, bg=ui.background)
        for text, command, side in (
            ("‹ MEDIA", show_media, tk.LEFT),
            ("HOME", show_home, tk.RIGHT),
        ):
            tk.Button(
                self, text=text, command=command,
                bg=ui.control_background, fg=ui.control_text,
                activebackground=ui.control_active, activeforeground=ui.text,
                relief=tk.FLAT, bd=0, font=("Sans", 9, "bold"),
                padx=12, pady=6, cursor="hand2",
            ).pack(side=side)
