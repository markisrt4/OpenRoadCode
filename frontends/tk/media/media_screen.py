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
YOUTUBE_SURFACE = "#171717"
YOUTUBE_BORDER = "#343434"
NETFLIX_SURFACE = "#080808"
NETFLIX_BORDER = "#3A1014"
BRAND_TEXT = "#FFFFFF"
BRAND_MUTED = "#AFAFAF"


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
        """Build the provider hub in the application's shared content host."""
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("Media")
        self._host.set_screen_status("Choose a media source")

        theme = self._theme_bundle().ui
        root = tk.Frame(self._host.screen_parent, bg=theme.background)
        root.pack(fill=tk.BOTH, expand=True)

        heading = tk.Frame(root, bg=theme.background)
        heading.pack(fill=tk.X, padx=14, pady=(10, 4))
        tk.Label(
            heading,
            text="MEDIA",
            bg=theme.background,
            fg=theme.text,
            font=("Sans", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            heading,
            text="Music, video, and streaming",
            bg=theme.background,
            fg=theme.text_muted,
            font=("Sans", 10),
        ).pack(anchor="w")

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
            category="WATCH",
            subtitle="Video, creators, live",
            detail="Launch straight into the YouTube kiosk with your retained profile.",
            accent=YOUTUBE_RED,
            command=self._show_youtube,
            action="WATCH YOUTUBE",
            surface=YOUTUBE_SURFACE,
            border=YOUTUBE_BORDER,
            title_color=BRAND_TEXT,
            muted_color=BRAND_MUTED,
        )
        youtube.grid(row=0, column=1, sticky="nsew", padx=6, pady=4)

        netflix = self._media_card(
            grid,
            glyph="netflix",
            title="NETFLIX",
            category="STREAMING",
            subtitle="Movies & series",
            detail="Resume Netflix directly in its kiosk with your retained browser profile.",
            accent=NETFLIX_RED,
            command=self._show_netflix,
            action="OPEN NETFLIX",
            surface=NETFLIX_SURFACE,
            border=NETFLIX_BORDER,
            title_color=BRAND_TEXT,
            muted_color="#8F8F8F",
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
        title_color: str | None = None,
        muted_color: str | None = None,
    ) -> tk.Frame:
        theme = self._theme_bundle().ui
        card_surface = surface or theme.surface
        card_border = border or theme.border
        card_title = title_color or theme.text
        card_muted = muted_color or theme.text_muted

        card = tk.Frame(
            parent,
            bg=card_surface,
            highlightthickness=1,
            highlightbackground=card_border,
            cursor="hand2",
        )
        self._brand_header(card, glyph, accent, card_surface)

        body = tk.Frame(card, bg=card_surface)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=(14, 12))

        top = tk.Frame(body, bg=card_surface)
        top.pack(fill=tk.X)
        glyph_box = tk.Frame(
            top,
            bg=theme.background,
            width=52,
            height=52,
            highlightthickness=1,
            highlightbackground=card_border,
        )
        glyph_box.pack(side=tk.LEFT)
        glyph_box.pack_propagate(False)
        self._provider_logo(glyph_box, glyph, accent)

        identity = tk.Frame(top, bg=card_surface)
        identity.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0))
        tk.Label(
            identity,
            text=title,
            bg=card_surface,
            fg=card_title,
            font=("Sans", 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            identity,
            text=category,
            bg=card_surface,
            fg=accent,
            font=("Sans", 8, "bold"),
        ).pack(anchor="w", pady=(2, 0))

        tk.Label(
            body,
            text=subtitle,
            bg=card_surface,
            fg=card_title,
            font=("Sans", 12, "bold"),
        ).pack(anchor="w", pady=(18, 5))
        tk.Label(
            body,
            text=detail,
            bg=card_surface,
            fg=card_muted,
            font=("Sans", 9),
            justify=tk.LEFT,
            wraplength=220,
        ).pack(anchor="w")

        if glyph == "youtube":
            self._youtube_signature(body, card_surface, card_muted)
        elif glyph == "netflix":
            self._netflix_signature(body, card_surface)

        if action is not None:
            tk.Button(
                body,
                text=f"{action}   ›",
                command=command,
                bg=accent,
                fg="#FFFFFF",
                activebackground=accent,
                activeforeground="#FFFFFF",
                relief=tk.FLAT,
                bd=0,
                font=("Sans", 9, "bold"),
                padx=12,
                pady=9,
                cursor="hand2",
            ).pack(fill=tk.X, side=tk.BOTTOM, pady=(14, 0))

        self._bind_card(card, command)
        return card

    @staticmethod
    def _brand_header(
        card: tk.Frame,
        glyph: str,
        accent: str,
        surface: str,
    ) -> None:
        if glyph == "youtube":
            header = tk.Frame(card, bg=surface, height=9)
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            tk.Frame(header, bg=accent, width=82).pack(side=tk.LEFT, fill=tk.Y)
            return

        if glyph == "netflix":
            header = tk.Frame(card, bg="#000000", height=9)
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            tk.Frame(header, bg=accent, width=24).pack(side=tk.RIGHT, fill=tk.Y)
            return

        tk.Frame(card, bg=accent, height=6).pack(fill=tk.X)

    @staticmethod
    def _youtube_signature(
        parent: tk.Widget,
        background: str,
        muted: str,
    ) -> None:
        row = tk.Frame(parent, bg=background)
        row.pack(fill=tk.X, pady=(18, 0))
        tk.Label(
            row,
            text="▶",
            bg=YOUTUBE_RED,
            fg="#FFFFFF",
            font=("Sans", 8, "bold"),
            padx=6,
            pady=2,
        ).pack(side=tk.LEFT)
        tk.Label(
            row,
            text="  CREATOR VIDEO",
            bg=background,
            fg=muted,
            font=("Sans", 8, "bold"),
        ).pack(side=tk.LEFT)

    @staticmethod
    def _netflix_signature(parent: tk.Widget, background: str) -> None:
        row = tk.Frame(parent, bg=background)
        row.pack(fill=tk.X, pady=(18, 0))
        tk.Frame(row, bg=NETFLIX_RED, width=3, height=18).pack(side=tk.LEFT)
        tk.Label(
            row,
            text="  CINEMA · SERIES",
            bg=background,
            fg="#D6D6D6",
            font=("Sans", 8, "bold"),
        ).pack(side=tk.LEFT)

    def _spotify_card_actions(self, card: tk.Frame) -> None:
        theme = self._theme_bundle().ui
        body = card.winfo_children()[-1]
        actions = tk.Frame(body, bg=theme.surface)
        actions.pack(fill=tk.X, side=tk.BOTTOM, pady=(14, 0))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        tk.Button(
            actions,
            text="REMOTE",
            command=self._show_spotify_remote,
            bg="#181818",
            fg="#FFFFFF",
            activebackground="#282828",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 9, "bold"),
            pady=9,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        tk.Button(
            actions,
            text="PLAY HERE",
            command=self._show_spotify_local,
            bg=SPOTIFY_GREEN,
            fg="#000000",
            activebackground=SPOTIFY_GREEN,
            activeforeground="#000000",
            disabledforeground="#747474",
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 9, "bold"),
            pady=9,
            state=tk.NORMAL if self._spotify_local_available() else tk.DISABLED,
        ).grid(row=0, column=1, sticky="ew", padx=(3, 0))

    def _provider_logo(self, parent: tk.Widget, glyph: str, accent: str) -> None:
        if glyph == "spotify":
            parent.configure(bg=SPOTIFY_GREEN, highlightthickness=0)
            self._spotify_logo(parent, SPOTIFY_GREEN)
            return
        if glyph == "youtube":
            self._youtube_logo(parent)
            return
        if glyph == "netflix":
            self._netflix_logo(parent)
            return

        theme = self._theme_bundle().ui
        tk.Label(
            parent,
            text=glyph,
            bg=theme.background,
            fg=accent,
            font=("Sans", 22, "bold"),
        ).pack(fill=tk.BOTH, expand=True)

    @staticmethod
    def _spotify_logo(parent: tk.Widget, background: str) -> None:
        canvas = tk.Canvas(
            parent,
            width=48,
            height=48,
            bg=background,
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(fill=tk.BOTH, expand=True)
        for bounds, width in (
            ((8, 10, 41, 31), 4),
            ((10, 17, 39, 35), 3),
            ((12, 24, 37, 39), 3),
        ):
            canvas.create_arc(
                *bounds,
                start=24,
                extent=135,
                style=tk.ARC,
                outline="#000000",
                width=width,
            )

    @staticmethod
    def _youtube_logo(parent: tk.Widget) -> None:
        canvas = tk.Canvas(
            parent,
            width=52,
            height=52,
            bg="#111111",
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.create_rectangle(
            8,
            14,
            44,
            38,
            fill=YOUTUBE_RED,
            outline=YOUTUBE_RED,
        )
        canvas.create_polygon(
            23,
            19,
            23,
            33,
            34,
            26,
            fill="#FFFFFF",
            outline="#FFFFFF",
        )

    @staticmethod
    def _netflix_logo(parent: tk.Widget) -> None:
        tk.Label(
            parent,
            text="N",
            bg="#000000",
            fg=NETFLIX_RED,
            font=("Sans", 28, "bold"),
        ).pack(fill=tk.BOTH, expand=True)

    @staticmethod
    def _bind_card(widget: tk.Widget, command: Callable[[], None]) -> None:
        widget.bind("<Button-1>", lambda _event: command())
        for child in widget.winfo_children():
            if not isinstance(child, tk.Button):
                MediaScreen._bind_card(child, command)
