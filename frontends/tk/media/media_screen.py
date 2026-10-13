# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Top-level media navigation screen for the Tk ORC frontend."""

from __future__ import annotations

import tkinter as tk
from typing import cast
from collections.abc import Callable

from frontends.tk.offline_card import OfflineCardAppearance
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.media.spotify_account_if import SpotifyAccountRequests, SpotifyAccountSession, SpotifyAccountState
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle, ThemeMode
from ui.media.media_preview_if import MediaPreviewIf
from .media_preview import MediaPreview
from .spectrum_illustration import paint_spectrum_illustration

SPOTIFY_GREEN = "#1DB954"
YOUTUBE_RED = "#FF0033"
NETFLIX_RED = "#E50914"
YOUTUBE_MUSIC_RED = "#FF0000"


class MediaScreen(TkScreen):
    """Present the media-provider hub and route into provider screens."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        theme_bundle: Callable[[], ThemeBundle],
        show_spotify: Callable[[], None],
        show_youtube: Callable[[], None],
        show_youtube_music: Callable[[], None],
        show_netflix: Callable[[], None],
        show_visualizer: Callable[[], None] | None = None,
        show_spotify_remote: Callable[[], None] | None = None,
        show_spotify_local: Callable[[], None] | None = None,
        spotify_local_available: Callable[[], bool] | None = None,
        account_session: SpotifyAccountSession | None = None,
        show_account_configuration: Callable[[], None] | None = None,
        close_account_configuration: Callable[[], None] = lambda: None,
        online_allowed: Callable[[], bool] = lambda: True,
        preview: MediaPreviewIf | None = None,
    ) -> None:
        super().__init__(ScreenId("media"))
        self._host = host
        self._preview_handler = preview
        self._preview_widget: MediaPreview | None = None
        self._online_allowed = online_allowed
        self._theme_bundle = theme_bundle
        self._show_spotify = self._online_action(show_spotify)
        self._show_youtube = self._online_action(show_youtube)
        self._show_youtube_music = self._online_action(show_youtube_music)
        self._show_netflix = self._online_action(show_netflix)
        self._show_visualizer = show_visualizer
        self._show_spotify_remote = self._online_action(show_spotify_remote or show_spotify)
        self._show_spotify_local = self._online_action(show_spotify_local or show_spotify)
        self._spotify_local_available = spotify_local_available or (lambda: True)
        self._account_session = account_session
        self._show_account_configuration = show_account_configuration
        self._close_account_configuration = close_account_configuration
        self._account = SpotifyAccountState()
        self._account_handler: SpotifyAccountRequests | None = None
        self._configured_label: tk.Label | None = None
        self._connected_label: tk.Label | None = None
        self._account_button: tk.Button | None = None
        self._configuration_button: tk.Button | None = None

    def _online_action(self, action: Callable[[], None]) -> Callable[[], None]:
        def invoke() -> None:
            if not self._online_allowed():
                self._host.set_screen_status("Offline mode: online media unavailable")
                return
            action()
        return invoke

    def set_theme_mode(self, _mode: ThemeMode) -> None:
        """Rebuild the mounted media hub from the newly active CSS theme."""
        self.show()

    def hide(self) -> None:
        if self._preview_widget is not None:
            self._preview_widget.stop()
            self._preview_widget = None
        if self._account_session is not None:
            self._account_session.deactivate()
        self._close_account_configuration()
        self._configured_label = None
        self._connected_label = None
        self._account_button = None
        self._configuration_button = None

    def show(self) -> None:
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("Media")
        self._host.set_screen_status("" if self._online_allowed() else "Offline mode: streaming media unavailable")

        theme = self._theme_bundle().ui
        root = tk.Frame(self._host.screen_parent, bg=theme.background)
        root.pack(fill=tk.BOTH, expand=True)

        heading = tk.Frame(root, bg=theme.background)
        heading.pack(fill=tk.X, padx=12, pady=(8, 6))
        identity = tk.Frame(heading, bg=theme.background)
        identity.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            identity,
            text="MEDIA",
            bg=theme.background,
            fg=theme.text,
            font=("Sans", 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            identity,
            text="Music, video, and streaming",
            bg=theme.background,
            fg=theme.text_muted,
            font=("Sans", 10),
        ).pack(anchor="w")

        grid = tk.Frame(root, bg=theme.background)
        grid.pack(fill=tk.BOTH, expand=True, padx=6, pady=(2, 8))
        for column in range(2):
            grid.grid_columnconfigure(column, weight=1, uniform="media")
        grid.grid_rowconfigure(0, weight=1, uniform="media")
        grid.grid_rowconfigure(1, weight=1, uniform="media")

        spotify = self._media_card(
            grid,
            glyph="spotify",
            title="SPOTIFY",
            category="MUSIC",
            subtitle="Your music, your device",
            detail="Remote controls your Connect device. Play here uses ORC.",
            accent=SPOTIFY_GREEN,
            command=self._show_spotify,
        )
        spotify.grid(row=0, column=0, sticky="nsew", padx=6, pady=4)
        self._spotify_card_actions(spotify)
        if self._show_account_configuration is not None:
            self._spotify_configuration(spotify)
        if self._account_session is not None:
            self._spotify_account_actions(spotify)

        youtube = self._media_card(
            grid,
            glyph="youtube",
            title="YOUTUBE",
            category="VIDEO",
            subtitle="Creators, clips & live",
            detail="Videos and live streams with your saved profile.",
            accent=YOUTUBE_RED,
            command=self._show_youtube,
            action="WATCH YOUTUBE",
            feature="youtube",
        )
        youtube.grid(row=0, column=1, sticky="nsew", padx=6, pady=4)

        music = tk.Frame(grid, bg=theme.background)
        music.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)
        music.grid_columnconfigure(0, weight=1)
        music.grid_rowconfigure(0, weight=1)
        youtube_music = self._media_card(
            music,
            glyph="youtube_music",
            title="YOUTUBE MUSIC",
            category="MUSIC",
            subtitle="Your music, mixes & library",
            detail="YouTube Music integration is coming soon.",
            accent=YOUTUBE_MUSIC_RED,
            command=self._show_youtube_music,
            action=None,
            feature="youtube_music",
        )
        youtube_music.grid(row=0, column=0, sticky="nsew")
        if self._show_visualizer is not None:
            self._visualizer_card(music).grid(
                row=1, column=0, sticky="ew", pady=(6, 0),
            )

        netflix = self._media_card(
            grid,
            glyph="netflix",
            title="NETFLIX",
            category="MOVIES + SERIES",
            subtitle="Continue watching",
            detail="Movies and series with your saved profile.",
            accent=NETFLIX_RED,
            command=self._show_netflix,
            action="OPEN NETFLIX",
            feature="netflix",
        )
        netflix.grid(row=1, column=1, sticky="nsew", padx=6, pady=4)

        if not self._online_allowed():
            for card in (spotify, youtube, youtube_music, netflix):
                OfflineCardAppearance(card).set_online(False)

        if self._account_session is not None:
            self._account_session.activate(self)

    def _visualizer_card(self, parent: tk.Misc) -> tk.Frame:
        """Share the music column with an offline-capable visualizer shortcut."""
        theme = self._theme_bundle().ui
        show_visualizer = self._show_visualizer
        if show_visualizer is None:
            raise RuntimeError("Visualizer action is unavailable")
        card = tk.Frame(parent, bg=theme.surface)
        canvas = tk.Canvas(
            card, height=60, bg=theme.surface, highlightthickness=0, bd=0,
            cursor="hand2",
        )
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.bind("<Configure>", lambda event: self._paint_visualizer(
            canvas, event.width, event.height))
        canvas.bind("<Button-1>", lambda _event: show_visualizer())
        tk.Button(
            card, text="Music visualizer   ›",
            command=show_visualizer,
            bg=theme.surface, fg=theme.text,
            activebackground=theme.control_active, activeforeground=theme.text,
            relief=tk.FLAT, bd=0, highlightthickness=0,
            font=("Sans", 10, "bold"), padx=8, pady=10,
        ).place(x=10, rely=0.5, anchor="w")
        return card

    def _paint_visualizer(self, canvas: tk.Canvas, width: int, height: int) -> None:
        """Draw a responsive spectrum illustration, rather than live audio data."""
        canvas.delete("all")
        paint_spectrum_illustration(canvas, width, height)

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
        feature: str | None = None,
    ) -> tk.Frame:
        theme = self._theme_bundle().ui
        card = tk.Frame(
            parent,
            bg=theme.surface,
            highlightthickness=1,
            highlightbackground=theme.border,
            cursor="hand2",
        )
        body = tk.Frame(card, bg=theme.surface)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=9)

        if glyph == "spotify" and self._preview_handler is not None:
            self._preview_widget = MediaPreview(
                body, handler=self._preview_handler, ui=theme,
                on_open=command,
            )
            self._preview_widget.pack(fill=tk.X)
        else:
            glow_accent = {
                "spotify": "#29c875", "youtube": "#ed4768",
                "youtube_music": "#f27876", "netflix": "#b73565",
            }[glyph]
            top = tk.Canvas(body, height=54, bg=theme.surface,
                            highlightthickness=0, bd=0, cursor="hand2")
            top.pack(fill=tk.X)
            glyph_box = tk.Frame(top, bg=theme.surface_alt, width=50, height=50,
                                 highlightthickness=0)
            glyph_box.pack_propagate(False)
            self._provider_logo(glyph_box, glyph)
            top.create_window(4, 27, window=glyph_box, anchor="w", tags="identity")
            top.create_text(64, 27, text=title, anchor="w", fill=theme.text,
                            font=("Sans", 14, "bold"), tags="identity")
            top.bind("<Configure>", lambda event: self._paint_provider_glow(
                top, event.width, event.height, glow_accent))
            card.bind("<Enter>", lambda _event: card.configure(
                highlightbackground=self._tint_color(card, theme.border, glow_accent, 0.45)))
            card.bind("<Leave>", lambda _event: card.configure(
                highlightbackground=theme.border))
            detail_label = tk.Label(
                body,
                text="Coming soon" if feature == "youtube_music" else detail,
                bg=theme.surface,
                fg=theme.text_muted,
                font=("Sans", 9),
                justify=tk.LEFT,
                anchor="w",
                wraplength=360,
            )
            detail_label.pack(anchor="w", fill=tk.X, pady=(6, 0))
            body.bind("<Configure>", lambda event: detail_label.configure(
                wraplength=max(1, event.width)))

        if action is not None:
            button = tk.Button(
                body,
                text=f"{action}   ›",
                state=tk.NORMAL if self._online_allowed() else tk.DISABLED,
                disabledforeground=theme.text_muted,
                command=command,
                bg=theme.control_background,
                fg=theme.text,
                activebackground=theme.control_active,
                activeforeground=theme.text,
                relief=tk.FLAT,
                bd=0,
                font=("Sans", 10, "bold"),
                padx=10,
                pady=6,
                cursor="hand2",
                highlightthickness=0,
            )
            button.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))

        self._bind_card(card, command)
        return card

    @staticmethod
    def _tint_color(widget: tk.Misc, base: str, accent: str, amount: float) -> str:
        """Blend a brand accent into the current theme instead of replacing it."""
        left = widget.winfo_rgb(base)
        right = widget.winfo_rgb(accent)
        return "#" + "".join(
            f"{round((a + (b - a) * amount) / 257):02x}"
            for a, b in zip(left, right)
        )

    def _paint_provider_glow(self, canvas: tk.Canvas, width: int, height: int,
                             accent: str) -> None:
        """Draw a soft brand wash near the logo, fading across the header."""
        canvas.delete("glow")
        if width < 2 or height < 2:
            return
        base = canvas.cget("bg")
        for index in range(32):
            amount = 0.28 * (1 - index / 31) ** 2
            canvas.create_rectangle(
                width * index / 32, 0, width * (index + 1) / 32 + 1, height,
                fill=self._tint_color(canvas, base, accent, amount),
                outline="", tags="glow",
            )
        canvas.tag_lower("glow")
        canvas.tag_raise("identity")

    def _youtube_feature(self, parent: tk.Widget) -> None:
        theme = self._theme_bundle().ui
        preview = tk.Canvas(
            parent,
            height=54,
            bg=theme.control_background,
            highlightthickness=0,
            bd=0,
        )
        preview.pack(fill=tk.X, pady=(18, 0))
        preview.create_rectangle(10, 6, 58, 32, fill=YOUTUBE_RED, outline=YOUTUBE_RED)
        preview.create_polygon(29, 11, 29, 27, 43, 19, fill="#FFFFFF", outline="#FFFFFF")
        preview.create_text(
            70,
            19,
            text="WATCH",
            anchor="w",
            fill=theme.text,
            font=("Sans", 15, "bold"),
        )

    def _youtube_music_feature(self, parent: tk.Widget) -> None:
        theme = self._theme_bundle().ui
        preview = tk.Canvas(parent, height=38, bg=theme.control_background, highlightthickness=0, bd=0)
        preview.pack(fill=tk.X, pady=(8, 0))
        preview.create_oval(10, 3, 44, 37, fill=YOUTUBE_MUSIC_RED, outline=YOUTUBE_MUSIC_RED)
        preview.create_oval(16, 9, 38, 31, fill=theme.control_background, outline=theme.text, width=2)
        preview.create_polygon(25, 14, 25, 26, 34, 20, fill="#FFFFFF", outline="#FFFFFF")
        preview.create_text(55, 20, text="MUSIC", anchor="w", fill=theme.text, font=("Sans", 12, "bold"))

    def _netflix_feature(self, parent: tk.Widget) -> None:
        theme = self._theme_bundle().ui
        banner = tk.Frame(
            parent,
            bg=theme.surface_alt,
            height=54,
            highlightthickness=1,
            highlightbackground=theme.border,
        )
        banner.pack(fill=tk.X, pady=(18, 0))
        banner.pack_propagate(False)
        tk.Label(
            banner,
            text="N",
            bg=theme.surface_alt,
            fg=NETFLIX_RED,
            font=("Sans", 28, "bold"),
        ).pack(side=tk.LEFT, padx=(12, 8))
        tk.Label(
            banner,
            text="CINEMA",
            bg=theme.surface_alt,
            fg=theme.text_muted,
            font=("Sans", 15, "bold"),
        ).pack(side=tk.LEFT)

    def set_spotify_account_handler(self, handler: SpotifyAccountRequests | None) -> None:
        self._account_handler = handler

    def set_spotify_account_state(self, state: SpotifyAccountState) -> None:
        self._account = state
        theme = self._theme_bundle().ui
        if self._configured_label is not None:
            self._configured_label.configure(text="APP CONFIGURED" if state.configured else "APP NOT CONFIGURED",
                fg=SPOTIFY_GREEN if state.configured else theme.text_muted)
        if self._connected_label is not None:
            self._connected_label.configure(text="ACCOUNT CONNECTED" if state.connected else "ACCOUNT NOT CONNECTED",
                fg=SPOTIFY_GREEN if state.connected else theme.text_muted)
        if self._account_button is not None:
            self._account_button.configure(text="Disconnect" if state.connected else "Connect account",
                state=tk.NORMAL if not state.busy and not state.loading and (state.connected or state.online) else tk.DISABLED,
                bg=theme.control_background if state.connected else SPOTIFY_GREEN,
                fg=theme.control_text if state.connected else "#000000")
        if self._configuration_button is not None:
            self._configuration_button.configure(text="Setup ✓" if state.configured else "Set up app",
                state=tk.DISABLED if state.busy else tk.NORMAL)
        if state.message:
            self._host.set_screen_status(state.message)

    def _request_account_action(self) -> None:
        handler = self._account_handler
        if handler is not None:
            if self._account.connected:
                handler.request_disconnect()
            else:
                handler.request_connect()

    @staticmethod
    def _card_body(card: tk.Frame) -> tk.Widget:
        return next(cast(tk.Widget, child) for child in card.winfo_children() if cast(tk.Widget, child).winfo_manager() == "pack")

    def _spotify_account_actions(self, card: tk.Frame) -> None:
        theme = self._theme_bundle().ui
        row = self._spotify_settings_row(card)
        self._account_button = tk.Button(row, text="Connect account", command=self._request_account_action,
            bg=theme.control_background, fg=theme.text_muted, disabledforeground=theme.text_muted,
            activebackground=theme.control_active, activeforeground=theme.text, relief=tk.FLAT,
            bd=0, highlightthickness=0, font=("Sans", 8, "bold"), padx=9, pady=5)
        self._account_button.pack(side=tk.LEFT)

    def _spotify_configuration(self, card: tk.Frame) -> None:
        theme = self._theme_bundle().ui
        row = self._spotify_settings_row(card)
        self._configuration_button = tk.Button(row, text="Set up app", command=self._show_account_configuration or (lambda: None),
            bg=theme.control_background, fg=theme.control_text, activebackground=theme.control_active,
            activeforeground=theme.text, relief=tk.FLAT, bd=0, highlightthickness=0,
            font=("Sans", 8, "bold"), padx=9, pady=5)
        self._configuration_button.pack(side=tk.RIGHT)

    def _spotify_settings_row(self, card: tk.Frame) -> tk.Frame:
        """Keep secondary account controls together inside the card body."""
        body = self._card_body(card)
        row = body.children.get("spotify_settings")
        if row is None:
            row = tk.Frame(body, name="spotify_settings", bg=self._theme_bundle().ui.surface)
            row.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        return cast(tk.Frame, row)

    def _spotify_card_actions(self, card: tk.Frame) -> None:
        theme = self._theme_bundle().ui
        # _media_card creates the body first and then overlays the accent strip,
        # so indexing the last child can accidentally select the accent. Find the
        # actual packed body instead.
        body = self._card_body(card)
        actions = tk.Frame(body, bg=theme.surface)
        actions.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        tk.Button(
            actions,
            text="REMOTE",
            state=tk.NORMAL if self._online_allowed() else tk.DISABLED,
            disabledforeground=theme.text_muted,
            command=self._show_spotify_remote,
            bg=theme.control_background,
            fg=theme.control_text,
            activebackground=theme.control_active,
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 10, "bold"),
            pady=7,
            highlightthickness=0,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        tk.Button(
            actions,
            text="PLAY HERE",
            command=self._show_spotify_local,
            bg=theme.control_background,
            fg=theme.text,
            activebackground=theme.control_active,
            activeforeground=theme.text,
            disabledforeground=theme.text_muted,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 10, "bold"),
            pady=7,
            state=tk.NORMAL if self._spotify_local_available() and self._online_allowed() else tk.DISABLED,
            highlightthickness=0,
        ).grid(row=0, column=1, sticky="ew", padx=(3, 0))

    def _provider_logo(self, parent: tk.Widget, glyph: str) -> None:
        if glyph == "spotify":
            parent.configure({"bg": SPOTIFY_GREEN, "highlightthickness": 0})
            canvas = tk.Canvas(
                parent,
                width=58,
                height=58,
                bg=SPOTIFY_GREEN,
                highlightthickness=0,
                bd=0,
            )
            canvas.pack(fill=tk.BOTH, expand=True)
            for bounds, width in (
                ((9, 12, 49, 35), 4),
                ((12, 20, 46, 40), 3),
                ((15, 28, 43, 45), 3),
            ):
                canvas.create_arc(
                    *bounds,
                    start=24,
                    extent=135,
                    style=tk.ARC,
                    outline="#000000",
                    width=width,
                )
            canvas.scale("all", 0, 0, 50 / 58, 50 / 58)
            return
        if glyph == "youtube_music":
            canvas = tk.Canvas(parent, width=58, height=58, bg="#111111", highlightthickness=0, bd=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            canvas.create_oval(7, 7, 51, 51, fill=YOUTUBE_MUSIC_RED, outline=YOUTUBE_MUSIC_RED)
            canvas.create_oval(14, 14, 44, 44, fill="#111111", outline="#FFFFFF", width=2)
            canvas.create_polygon(25, 20, 25, 38, 39, 29, fill="#FFFFFF", outline="#FFFFFF")
            canvas.scale("all", 0, 0, 50 / 58, 50 / 58)
            return
        if glyph == "youtube":
            canvas = tk.Canvas(
                parent,
                width=58,
                height=58,
                bg="#111111",
                highlightthickness=0,
                bd=0,
            )
            canvas.pack(fill=tk.BOTH, expand=True)
            canvas.create_rectangle(8, 16, 50, 42, fill=YOUTUBE_RED, outline=YOUTUBE_RED)
            canvas.create_polygon(24, 21, 24, 37, 37, 29, fill="#FFFFFF", outline="#FFFFFF")
            canvas.scale("all", 0, 0, 50 / 58, 50 / 58)
            return
        tk.Label(
            parent,
            text="N",
            bg="#000000",
            fg=NETFLIX_RED,
            font=("Sans", 28, "bold"),
        ).pack(fill=tk.BOTH, expand=True)

    @staticmethod
    def _bind_card(widget: tk.Misc, command: Callable[[], None]) -> None:
        widget.bind("<Button-1>", lambda _event: command())
        for child in widget.winfo_children():
            if not isinstance(child, tk.Button):
                MediaScreen._bind_card(child, command)
