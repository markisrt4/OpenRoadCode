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
        self._theme = theme_bundle().ui
        super().__init__(parent, bg=self._theme.background)

        self._button(
            "‹ MEDIA",
            show_media,
            selected=active == "media",
            accent=self._theme.control_active,
        ).pack(side=tk.LEFT)

        providers = tk.Frame(self, bg=self._theme.background)
        providers.pack(side=tk.LEFT, padx=(10, 0))
        for key, text, command, accent in (
            ("spotify", "SPOTIFY", show_spotify, SPOTIFY_GREEN),
            ("youtube", "YOUTUBE", show_youtube, YOUTUBE_RED),
            ("netflix", "NETFLIX", show_netflix, NETFLIX_RED),
        ):
            self._provider_button(
                providers,
                text,
                command,
                selected=key == active,
                accent=accent,
                dark_text=key == "spotify",
            ).pack(side=tk.LEFT, padx=(0, 4))

        self._button(
            "HOME",
            show_home,
            selected=False,
            accent=self._theme.control_active,
        ).pack(side=tk.RIGHT)

    def _button(
        self,
        text: str,
        command: Callable[[], None],
        *,
        selected: bool,
        accent: str,
    ) -> tk.Button:
        return tk.Button(
            self,
            text=text,
            command=command,
            bg=accent if selected else self._theme.surface,
            fg=self._theme.text,
            activebackground=accent,
            activeforeground=self._theme.text,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 9, "bold"),
            padx=12,
            pady=6,
            cursor="hand2",
        )

    def _provider_button(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
        *,
        selected: bool,
        accent: str,
        dark_text: bool,
    ) -> tk.Button:
        selected_foreground = "#000000" if dark_text else "#FFFFFF"
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=accent if selected else self._theme.surface,
            fg=selected_foreground if selected else self._theme.text,
            activebackground=accent,
            activeforeground=selected_foreground,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 9, "bold"),
            padx=12,
            pady=6,
            cursor="hand2",
        )
