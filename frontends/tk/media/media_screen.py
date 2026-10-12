# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Top-level media navigation screen for the Tk ORC frontend."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from frontends.tk.offline_card import OfflineCardAppearance
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle, ThemeMode
from ui.media.media_preview_if import MediaPreviewIf
from .media_preview import MediaPreview

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
        configure_spotify: Callable[[str], str] | None = None,
        spotify_client_id: Callable[[], str | None] | None = None,
        spotify_account_connected: Callable[[], bool] | None = None,
        connect_spotify: Callable[[], str] | None = None,
        disconnect_spotify: Callable[[], str] | None = None,
        online_allowed: Callable[[], bool] = lambda: True,
        preview: MediaPreviewIf | None = None,
    ) -> None:
        super().__init__(ScreenId("media"))
        self._host = host
        self._preview_handler = preview
        self._preview_widget = None
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
        self._configure_spotify = configure_spotify
        self._spotify_client_id = spotify_client_id or (lambda: None)
        self._spotify_account_connected = spotify_account_connected or (lambda: False)
        self._connect_spotify = connect_spotify
        self._disconnect_spotify = disconnect_spotify

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
        if self._configure_spotify is not None:
            self._spotify_configuration(spotify)
        if self._connect_spotify is not None:
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

    def hide(self) -> None:
        """Release polling before the hub is hidden or rebuilt."""
        if self._preview_widget is not None:
            self._preview_widget.stop()
            self._preview_widget = None

    def _visualizer_card(self, parent: tk.Misc) -> tk.Frame:
        """Share the music column with an offline-capable visualizer shortcut."""
        theme = self._theme_bundle().ui
        card = tk.Frame(parent, bg=theme.surface)
        canvas = tk.Canvas(
            card, height=60, bg=theme.surface, highlightthickness=0, bd=0,
            cursor="hand2",
        )
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.bind("<Configure>", lambda event: self._paint_visualizer(
            canvas, event.width, event.height))
        canvas.bind("<Button-1>", lambda _event: self._show_visualizer())
        tk.Button(
            card, text="Music visualizer   ›",
            command=self._show_visualizer,
            bg=theme.surface, fg=theme.text,
            activebackground=theme.control_active, activeforeground=theme.text,
            relief=tk.FLAT, bd=0, highlightthickness=0,
            font=("Sans", 10, "bold"), padx=8, pady=10,
        ).place(x=10, rely=0.5, anchor="w")
        return card

    def _paint_visualizer(self, canvas: tk.Canvas, width: int, height: int) -> None:
        """Draw a responsive spectrum illustration, rather than live audio data."""
        canvas.delete("all")
        if width < 2 or height < 2:
            return
        base = tuple(value // 256 for value in canvas.winfo_rgb(canvas.cget("bg")))

        def mix(left, right, amount):
            return "#" + "".join(f"{round(a + (b - a) * amount):02x}"
                                 for a, b in zip(left, right))

        palette = ((35, 210, 186), (66, 145, 245), (165, 104, 238))
        profile = (0.24, 0.40, 0.32, 0.62, 0.85, 0.56, 0.96, 0.72,
                   0.48, 0.68, 0.38, 0.54)
        count = 36
        step = width / count
        for index in range(count):
            position = index / (count - 1) * 2
            segment = min(1, int(position))
            color = mix(palette[segment], palette[segment + 1], position - segment)
            rgb = tuple(int(color[offset:offset + 2], 16) for offset in (1, 3, 5))
            x = index * step
            canvas.create_rectangle(x, 0, x + step + 1, height,
                                    fill=mix(base, rgb, 0.10), outline="")
            bar_height = height * 0.72 * profile[index % len(profile)]
            # The title occupies the left side; the spectrum shines on the right.
            strength = 0.22 if index < count * 0.48 else 0.85
            canvas.create_rectangle(
                x + step * 0.2, (height - bar_height) / 2,
                x + step * 0.8, (height + bar_height) / 2,
                fill=mix(base, rgb, strength), outline="",
            )

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

    def show_spotify_configuration(self) -> None:
        """Open the shared Spotify application configuration dialog."""
        self._show_spotify_configuration_dialog()

    def run_spotify_account_action(self, disconnect: bool) -> None:
        """Run the shared Spotify account action from any media surface."""
        if not disconnect and not self._online_allowed():
            self._host.set_screen_status("Offline mode: Spotify sign-in unavailable")
            return
        action = self._disconnect_spotify if disconnect else self._connect_spotify
        if action is None:
            return
        self._host.set_screen_status(
            "Disconnecting Spotify…" if disconnect else "Opening Spotify authorization…"
        )

        def worker() -> None:
            try:
                message = action()
            except Exception as exc:
                message = f"Spotify: {exc}"
            self._host.schedule_ui_callback(0, lambda: self._spotify_action_complete(message))

        import threading
        threading.Thread(target=worker, name="spotify-authorization", daemon=True).start()

    def _spotify_account_actions(self, card: tk.Frame) -> None:
        """Show Spotify account authorization state and browser OAuth action."""
        theme = self._theme_bundle().ui
        connected = self._spotify_account_connected()
        row = self._spotify_settings_row(card)

        tk.Button(
            row,
            text="Disconnect" if connected else "Connect account",
            state=tk.NORMAL if connected or self._online_allowed() else tk.DISABLED,
            disabledforeground=theme.text_muted,
            command=lambda: self.run_spotify_account_action(connected),
            bg=theme.control_background,
            fg=theme.text_muted,
            activebackground=theme.control_active,
            activeforeground=theme.text,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 8, "bold"),
            padx=9,
            pady=5,
            highlightthickness=0,
        ).pack(side=tk.LEFT)

    def _spotify_action_complete(self, message: str) -> None:
        self._host.set_screen_status(message)
        self.show()

    def _spotify_configuration(self, card: tk.Frame) -> None:
        """Expose Spotify application configuration without requiring a shell."""
        theme = self._theme_bundle().ui
        configured = self._spotify_client_id()
        row = self._spotify_settings_row(card)
        tk.Button(
            row,
            text="Setup ✓" if configured else "Set up app",
            command=self._show_spotify_configuration_dialog,
            bg=theme.control_background,
            fg=theme.control_text,
            activebackground=theme.control_active,
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 8, "bold"),
            padx=9,
            pady=5,
            highlightthickness=0,
        ).pack(side=tk.RIGHT)

    def _spotify_settings_row(self, card: tk.Frame) -> tk.Frame:
        """Keep secondary account controls together inside the card body."""
        body = next(child for child in card.winfo_children()
                    if child.winfo_manager() == "pack")
        row = body.children.get("spotify_settings")
        if row is None:
            row = tk.Frame(body, name="spotify_settings", bg=self._theme_bundle().ui.surface)
            row.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        return row

    def _show_spotify_configuration_dialog(self) -> None:
        theme = self._theme_bundle().ui
        dialog = tk.Toplevel(self._host.screen_parent)
        dialog.title("Spotify configuration")
        dialog.configure(bg=theme.background)
        dialog.transient(self._host.screen_parent.winfo_toplevel())
        dialog.grab_set()

        tk.Label(
            dialog, text="SPOTIFY APPLICATION", bg=theme.background, fg=theme.text,
            font=("Sans", 14, "bold"),
        ).pack(anchor="w", padx=18, pady=(16, 4))
        tk.Label(
            dialog,
            text="Enter the Client ID from your Spotify developer application. "
                 "OpenRoadCode uses OAuth PKCE, so no client secret is required.",
            bg=theme.background, fg=theme.text_muted, justify=tk.LEFT, wraplength=460,
            font=("Sans", 9),
        ).pack(anchor="w", padx=18, pady=(0, 12))

        client_id = tk.StringVar(value=self._spotify_client_id() or "")
        entry = tk.Entry(
            dialog, textvariable=client_id, width=52,
            bg=theme.control_background, fg=theme.text, insertbackground=theme.text,
            selectbackground=theme.control_active, selectforeground=theme.control_text,
            relief=tk.FLAT, bd=0, highlightthickness=1,
            highlightbackground=theme.control_background, highlightcolor=theme.accent_primary,
        )
        entry.pack(fill=tk.X, padx=18)
        entry.focus_set()
        status = tk.StringVar(value="")
        tk.Label(
            dialog, textvariable=status, bg=theme.background, fg=theme.text_muted,
            font=("Sans", 8),
        ).pack(anchor="w", padx=18, pady=(5, 0))

        def save() -> None:
            try:
                message = self._configure_spotify(client_id.get().strip())
            except (ValueError, RuntimeError, OSError) as exc:
                status.set(str(exc))
                return
            dialog.destroy()
            self._host.set_screen_status(message)
            self.show()

        buttons = tk.Frame(dialog, bg=theme.background)
        buttons.pack(fill=tk.X, padx=18, pady=16)
        tk.Button(buttons, text="CANCEL", command=dialog.destroy, highlightthickness=0, bd=0, relief=tk.FLAT).pack(side=tk.RIGHT)
        tk.Button(
            buttons, text="SAVE", command=save, bg=SPOTIFY_GREEN, fg="#000000",
            relief=tk.FLAT, padx=14,
                            highlightthickness=0, bd=0,
        ).pack(side=tk.RIGHT, padx=(0, 8))

    def _spotify_card_actions(self, card: tk.Frame) -> None:
        theme = self._theme_bundle().ui
        # Keep action widgets inside the packed body of the provider card.
        body = next(
            child
            for child in card.winfo_children()
            if child.winfo_manager() == "pack"
        )
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
            parent.configure(bg=SPOTIFY_GREEN, highlightthickness=0)
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
    def _bind_card(widget: tk.Widget, command: Callable[[], None]) -> None:
        widget.bind("<Button-1>", lambda _event: command())
        for child in widget.winfo_children():
            if not isinstance(child, tk.Button):
                MediaScreen._bind_card(child, command)
