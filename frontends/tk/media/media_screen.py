# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Top-level media navigation screen for the Tk ORC frontend."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle

SPOTIFY_GREEN = "#1DB954"
YOUTUBE_RED = "#FF0033"
NETFLIX_RED = "#E50914"


class MediaScreen(TkScreen):
    """Present the media-provider hub and route into provider screens."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        theme_bundle: Callable[[], ThemeBundle],
        show_spotify: Callable[[], None],
        show_youtube: Callable[[], None],
        show_netflix: Callable[[], None],
    ) -> None:
        super().__init__(ScreenId("media"))
        self._host = host
        self._theme_bundle = theme_bundle
        self._show_spotify = show_spotify
        self._show_youtube = show_youtube
        self._show_netflix = show_netflix

    def show(self) -> None:
        """Build the provider hub in the application's shared content host."""
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("Media")
        self._host.set_screen_status("Choose a media source")

        theme = self._theme_bundle().ui
        root = tk.Frame(self._host.screen_parent, bg=theme.background)
        root.pack(fill=tk.BOTH, expand=True)

        heading = tk.Frame(root, bg=theme.background)
        heading.pack(fill=tk.X, padx=16, pady=(14, 8))
        tk.Label(
            heading,
            text="MEDIA",
            bg=theme.background,
            fg=theme.text,
            font=("Sans", 22, "bold"),
        ).pack(anchor="w")
        tk.Label(
            heading,
            text="Music, video, and streaming",
            bg=theme.background,
            fg=theme.text_muted,
            font=("Sans", 10),
        ).pack(anchor="w")

        grid = tk.Frame(root, bg=theme.background)
        grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 14))
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1, uniform="media")
        grid.grid_rowconfigure(0, weight=1)

        cards = (
            ("SPOTIFY", "MUSIC", "Now playing, library, playlists, and history", SPOTIFY_GREEN, self._show_spotify),
            ("YOUTUBE", "VIDEO", "Watch YouTube in the ORC media surface", YOUTUBE_RED, self._show_youtube),
            ("NETFLIX", "STREAM", "Open Netflix with the retained browser profile", NETFLIX_RED, self._show_netflix),
        )
        for column, (title, category, detail, accent, command) in enumerate(cards):
            self._card(
                grid,
                title=title,
                category=category,
                detail=detail,
                accent=accent,
                command=command,
            ).grid(row=0, column=column, sticky="nsew", padx=6, pady=4)

    def _card(
        self,
        parent: tk.Misc,
        *,
        title: str,
        category: str,
        detail: str,
        accent: str,
        command: Callable[[], None],
    ) -> tk.Frame:
        theme = self._theme_bundle().ui
        card = tk.Frame(
            parent,
            bg=theme.surface,
            highlightthickness=1,
            highlightbackground=theme.border,
        )
        tk.Frame(card, bg=accent, height=5).pack(fill=tk.X)
        body = tk.Frame(card, bg=theme.surface, padx=18, pady=16)
        body.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            body,
            text=category,
            bg=theme.surface,
            fg=accent,
            font=("Sans", 8, "bold"),
        ).pack(anchor="w")
        tk.Label(
            body,
            text=title,
            bg=theme.surface,
            fg=theme.text,
            font=("Sans", 18, "bold"),
        ).pack(anchor="w", pady=(6, 8))
        tk.Label(
            body,
            text=detail,
            bg=theme.surface,
            fg=theme.text_muted,
            justify=tk.LEFT,
            wraplength=210,
            font=("Sans", 10),
        ).pack(anchor="w")
        tk.Button(
            body,
            text=f"OPEN {title}",
            command=command,
            bg=accent,
            fg="#000000" if title == "SPOTIFY" else "#ffffff",
            activebackground=accent,
            activeforeground="#000000" if title == "SPOTIFY" else "#ffffff",
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 9, "bold"),
            pady=9,
        ).pack(fill=tk.X, side=tk.BOTTOM, pady=(16, 0))
        return card
