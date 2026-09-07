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
YOUTUBE_SURFACE = "#202020"
YOUTUBE_BORDER = "#3B3B3B"
NETFLIX_SURFACE = "#050505"
NETFLIX_BORDER = "#401015"


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
        show_spotify_remote: Callable[[], None] | None = None,
        show_spotify_local: Callable[[], None] | None = None,
        spotify_local_available: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(ScreenId("media"))
        self._host = host
        self._theme_bundle = theme_bundle
        self._show_spotify = show_spotify
        self._show_youtube = show_youtube
        self._show_netflix = show_netflix
        self._show_spotify_remote = show_spotify_remote or show_spotify
        self._show_spotify_local = show_spotify_local or show_spotify
        self._spotify_local_available = spotify_local_available or (lambda: True)

    def show(self) -> None:
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("Media")
        self._host.set_screen_status("Choose a media source")

        theme = self._theme_bundle().ui
        root = tk.Frame(self._host.screen_parent, bg=theme.background)
        root.pack(fill=tk.BOTH, expand=True)

        heading = tk.Frame(root, bg=theme.background)
        heading.pack(fill=tk.X, padx=14, pady=(10, 4))
        tk.Label(heading, text="MEDIA", bg=theme.background, fg=theme.text, font=("Sans", 20, "bold")).pack(anchor="w")
        tk.Label(heading, text="Music, video, and streaming", bg=theme.background, fg=theme.text_muted, font=("Sans", 10)).pack(anchor="w")

        grid = tk.Frame(root, bg=theme.background)
        grid.pack(fill=tk.BOTH, expand=True, padx=6, pady=(2, 8))
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1, uniform="media")
        grid.grid_rowconfigure(0, weight=1)

        spotify = self._media_card(
            grid,
            glyph="spotify",
            title="SPOTIFY",
            category="MUSIC",
            subtitle="Now playing",
            detail="Artwork, lyrics, library, playlists and music video.",
            accent=SPOTIFY_GREEN,
            command=self._show_spotify,
        )
        spotify.grid(row=0, column=0, sticky="nsew", padx=6, pady=4)
        self._spotify_card_actions(spotify)

        youtube = self._media_card(
            grid,
            glyph="youtube",
            title="YOUTUBE",
            category="VIDEO",
            subtitle="Creators, clips & live",
            detail="Open straight into YouTube with your retained profile.",
            accent=YOUTUBE_RED,
            command=self._show_youtube,
            action="WATCH YOUTUBE",
            surface=YOUTUBE_SURFACE,
            border=YOUTUBE_BORDER,
            feature="youtube",
        )
        youtube.grid(row=0, column=1, sticky="nsew", padx=6, pady=4)

        netflix = self._media_card(
            grid,
            glyph="netflix",
            title="NETFLIX",
            category="MOVIES + SERIES",
            subtitle="Continue watching",
            detail="Open your Netflix profile directly in the ORC kiosk.",
            accent=NETFLIX_RED,
            command=self._show_netflix,
            action="OPEN NETFLIX",
            surface=NETFLIX_SURFACE,
            border=NETFLIX_BORDER,
            feature="netflix",
        )
        netflix.grid(row=0, column=2, sticky="nsew", padx=6, pady=4)

    def _media_card(
        self,
        parent: tk.Misc,
        *,
        glyph: str,
        title: str,
        category: str,
        subtitle: str,
        detail: str,
        accent: str,
        command: Callable[[], None],
        action: str | None = None,
        surface: str | None = None,
        border: str | None = None,
        feature: str | None = None,
    ) -> tk.Frame:
        theme = self._theme_bundle().ui
        card_surface = surface or theme.surface
        card_border = border or theme.border

        card = tk.Frame(parent, bg=card_surface, highlightthickness=1, highlightbackground=card_border, cursor="hand2")
        body = tk.Frame(card, bg=card_surface)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=14)

        top = tk.Frame(body, bg=card_surface)
        top.pack(fill=tk.X)
        glyph_box = tk.Frame(top, bg=theme.background, width=58, height=58, highlightthickness=1, highlightbackground=card_border)
        glyph_box.pack(side=tk.LEFT)
        glyph_box.pack_propagate(False)
        self._provider_logo(glyph_box, glyph)

        identity = tk.Frame(top, bg=card_surface)
        identity.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0))
        title_fg = NETFLIX_RED if feature == "netflix" else theme.text
        tk.Label(identity, text=title, bg=card_surface, fg=title_fg, font=("Sans", 16, "bold")).pack(anchor="w")
        tk.Label(identity, text=category, bg=card_surface, fg=accent, font=("Sans", 8, "bold")).pack(anchor="w", pady=(2, 0))

        if feature == "youtube":
            self._youtube_feature(body)
        elif feature == "netflix":
            self._netflix_feature(body)

        tk.Label(body, text=subtitle, bg=card_surface, fg=theme.text, font=("Sans", 12, "bold")).pack(anchor="w", pady=(16, 5))
        tk.Label(body, text=detail, bg=card_surface, fg=theme.text_muted, font=("Sans", 9), justify=tk.LEFT, wraplength=220).pack(anchor="w")

        if action is not None:
            if feature == "netflix":
                button = tk.Button(body, text=f"{action}   ›", command=command, bg="#000000", fg=NETFLIX_RED, activebackground="#151515", activeforeground="#FFFFFF", relief=tk.FLAT, bd=0, highlightthickness=1, highlightbackground=NETFLIX_RED, font=("Sans", 9, "bold"), padx=12, pady=9, cursor="hand2")
            else:
                button = tk.Button(body, text=f"{action}   ›", command=command, bg=accent, fg="#FFFFFF", activebackground=accent, activeforeground="#FFFFFF", relief=tk.FLAT, bd=0, font=("Sans", 9, "bold"), padx=12, pady=9, cursor="hand2")
            button.pack(fill=tk.X, side=tk.BOTTOM, pady=(14, 0))

        self._bind_card(card, command)
        return card

    @staticmethod
    def _youtube_feature(parent: tk.Widget) -> None:
        preview = tk.Canvas(parent, height=54, bg="#111111", highlightthickness=0, bd=0)
        preview.pack(fill=tk.X, pady=(18, 0))
        preview.create_rectangle(10, 9, 70, 45, fill=YOUTUBE_RED, outline=YOUTUBE_RED)
        preview.create_polygon(35, 17, 35, 37, 52, 27, fill="#FFFFFF", outline="#FFFFFF")
        preview.create_text(84, 27, text="WATCH", anchor="w", fill="#FFFFFF", font=("Sans", 10, "bold"))

    @staticmethod
    def _netflix_feature(parent: tk.Widget) -> None:
        banner = tk.Frame(parent, bg="#000000", height=54, highlightthickness=1, highlightbackground=NETFLIX_BORDER)
        banner.pack(fill=tk.X, pady=(18, 0))
        banner.pack_propagate(False)
        tk.Label(banner, text="N", bg="#000000", fg=NETFLIX_RED, font=("Sans", 28, "bold")).pack(side=tk.LEFT, padx=(12, 8))
        tk.Label(banner, text="CINEMA", bg="#000000", fg="#D6D6D6", font=("Sans", 9, "bold")).pack(side=tk.LEFT)

    def _spotify_card_actions(self, card: tk.Frame) -> None:
        theme = self._theme_bundle().ui
        body = card.winfo_children()[-1]
        actions = tk.Frame(body, bg=theme.surface)
        actions.pack(fill=tk.X, side=tk.BOTTOM, pady=(14, 0))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        tk.Button(actions, text="REMOTE", command=self._show_spotify_remote, bg="#181818", fg="#FFFFFF", activebackground="#282828", activeforeground="#FFFFFF", relief=tk.FLAT, bd=0, font=("Sans", 9, "bold"), pady=9).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        tk.Button(actions, text="PLAY HERE", command=self._show_spotify_local, bg=SPOTIFY_GREEN, fg="#000000", activebackground=SPOTIFY_GREEN, activeforeground="#000000", disabledforeground="#747474", relief=tk.FLAT, bd=0, font=("Sans", 9, "bold"), pady=9, state=tk.NORMAL if self._spotify_local_available() else tk.DISABLED).grid(row=0, column=1, sticky="ew", padx=(3, 0))

    def _provider_logo(self, parent: tk.Widget, glyph: str) -> None:
        if glyph == "spotify":
            parent.configure(bg=SPOTIFY_GREEN, highlightthickness=0)
            canvas = tk.Canvas(parent, width=58, height=58, bg=SPOTIFY_GREEN, highlightthickness=0, bd=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            for bounds, width in (((9, 12, 49, 35), 4), ((12, 20, 46, 40), 3), ((15, 28, 43, 45), 3)):
                canvas.create_arc(*bounds, start=24, extent=135, style=tk.ARC, outline="#000000", width=width)
            return
        if glyph == "youtube":
            canvas = tk.Canvas(parent, width=58, height=58, bg="#111111", highlightthickness=0, bd=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            canvas.create_rectangle(8, 16, 50, 42, fill=YOUTUBE_RED, outline=YOUTUBE_RED)
            canvas.create_polygon(24, 21, 24, 37, 37, 29, fill="#FFFFFF", outline="#FFFFFF")
            return
        tk.Label(parent, text="N", bg="#000000", fg=NETFLIX_RED, font=("Sans", 31, "bold")).pack(fill=tk.BOTH, expand=True)

    @staticmethod
    def _bind_card(widget: tk.Widget, command: Callable[[], None]) -> None:
        widget.bind("<Button-1>", lambda _event: command())
        for child in widget.winfo_children():
            if not isinstance(child, tk.Button):
                MediaScreen._bind_card(child, command)
