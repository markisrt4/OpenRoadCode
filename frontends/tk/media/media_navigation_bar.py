# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared provider navigation for integrated media screens."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.theme import ThemeBundle

SPOTIFY_GREEN = "#1DB954"
YOUTUBE_RED = "#FF0033"
NETFLIX_RED = "#E50914"


class MediaNavigationBar(tk.Frame):
    """Provide direct navigation between the media hub and provider screens."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        theme_bundle: Callable[[], ThemeBundle],
        active: str,
        show_media: Callable[[], None],
        show_spotify: Callable[[], None],
        show_youtube: Callable[[], None],
        show_netflix: Callable[[], None],
    ) -> None:
        theme = theme_bundle().ui
        super().__init__(parent, bg=theme.background)

        items = (
            ("media", "‹ MEDIA", show_media, theme.control_active),
            ("spotify", "SPOTIFY", show_spotify, SPOTIFY_GREEN),
            ("youtube", "YOUTUBE", show_youtube, YOUTUBE_RED),
            ("netflix", "NETFLIX", show_netflix, NETFLIX_RED),
        )
        for key, text, command, accent in items:
            selected = key == active
            button = tk.Button(
                self,
                text=text,
                command=command,
                bg=accent if selected else theme.surface,
                fg="#000000" if selected and key == "spotify" else theme.text,
                activebackground=accent,
                activeforeground="#000000" if key == "spotify" else "#FFFFFF",
                relief=tk.FLAT,
                bd=0,
                font=("Sans", 9, "bold"),
                padx=12,
                pady=6,
                cursor="hand2",
            )
            button.pack(side=tk.LEFT, padx=(0, 4))
