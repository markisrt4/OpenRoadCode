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
    """Provide media-hub, provider, and Home navigation."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        theme_bundle: Callable[[], ThemeBundle],
        active: str,
        show_media: Callable[[], None],
        show_home: Callable[[], None],
        show_spotify: Callable[[], None],
        show_youtube: Callable[[], None],
        show_netflix: Callable[[], None],
    ) -> None:
        theme = theme_bundle().ui
        super().__init__(parent, bg=theme.background)

        self._button(
            "‹ MEDIA",
            show_media,
            selected=active == "media",
            accent=theme.control_active,
            foreground=theme.text,
        ).pack(side=tk.LEFT)

        providers = tk.Frame(self, bg=theme.background)
        providers.pack(side=tk.LEFT, padx=(10, 0))
        for key, text, command, accent in (
            ("spotify", "SPOTIFY", show_spotify, SPOTIFY_GREEN),
            ("youtube", "YOUTUBE", show_youtube, YOUTUBE_RED),
            ("netflix", "NETFLIX", show_netflix, NETFLIX_RED),
        ):
            self._button(
                text,
                command,
                selected=key == active,
                accent=accent,
                foreground="#000000" if key == "spotify" else theme.text,
            ).pack(side=tk.LEFT, padx=(0, 4))

        self._button(
            "HOME",
            show_home,
            selected=False,
            accent=theme.control_active,
            foreground=theme.text,
        ).pack(side=tk.RIGHT)

    def _button(
        self,
        text: str,
        command: Callable[[], None],
        *,
        selected: bool,
        accent: str,
        foreground: str,
    ) -> tk.Button:
        theme = self._theme_bundle().ui if hasattr(self, "_theme_bundle") else None
        if theme is None:
            background = accent if selected else self.cget("bg")
            normal_foreground = foreground
            active_foreground = foreground
        else:
            background = accent if selected else theme.surface
            normal_foreground = foreground if selected else theme.text
            active_foreground = foreground
        return tk.Button(
            self,
            text=text,
            command=command,
            bg=background,
            fg=normal_foreground,
            activebackground=accent,
            activeforeground=active_foreground,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 9, "bold"),
            padx=12,
            pady=6,
            cursor="hand2",
        )
