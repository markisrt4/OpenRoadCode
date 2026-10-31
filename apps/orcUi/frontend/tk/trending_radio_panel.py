# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Touch-friendly FM radio and MusicForge airplay split screen."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from ui.media.song_launch import SongDestination, SongLaunchRequest
from ui.radio.station_identity import station_label
from controllers.video import YouTubePlayer
from apps.orcUi.frontend.tk.trending_video_pane import TrendingVideoPane
from apps.orcUi.adapters.managed_browser_media_player import ManagedBrowserMediaPlayer
from ui.theme import ThemeBundle

PAGE_SIZE = 4


class TrendingRadioPanel(tk.Frame):
    """Keep real FM controls beside paged airplay cards, without scrollbars."""

    def __init__(self, parent: tk.Misc, *, theme: ThemeBundle,
                 on_back: Callable[[], None],
                 on_refresh: Callable[[str, str, str], None],
                 on_play: Callable[[SongLaunchRequest], None],
                 radio_factory: Callable[[tk.Misc, ThemeBundle], tk.Widget],
                 video_player: Callable[[], ManagedBrowserMediaPlayer | None] = lambda: None,
                 spotify_factory: Callable | None = None,
                 online_allowed: Callable[[], bool] = lambda: True) -> None:
        ui = theme.ui
        super().__init__(parent, bg=ui.background)
        self._theme = theme
        self._on_refresh = on_refresh
        self._on_play = on_play
        self._radio_factory = radio_factory
        self._video_player = video_player
        self._spotify_factory = spotify_factory
        self._online_allowed = online_allowed
        self._spotify_pane = None
        self._video_pane: TrendingVideoPane | None = None
        self._songs: list[dict] = []
        self._kind = "songs"
        self._selected: dict | None = None
        self._page = 0
        self._station = tk.StringVar(value="All stations")
        self._period = tk.StringVar(value="7d")
        # Disable geometry propagation: browser and SDR have different requested widths.
        self.grid_columnconfigure(0, weight=3, uniform='trending_split')
        self.grid_columnconfigure(1, weight=2, uniform='trending_split')
        self.grid_rowconfigure(1, weight=1)

        header = tk.Frame(self, bg=ui.background)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=8)
        self._button(header, "‹ RADIO", on_back).pack(side=tk.LEFT)
        tk.Label(header, text="FM RADIO  /  TRENDING", bg=ui.background,
                 fg=ui.text, font=("Sans", 13, "bold")).pack(side=tk.LEFT, padx=16)

        left = tk.Frame(self, bg=ui.background)
        left.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(0, 12))
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)
        left.grid_propagate(False)
        self._left = left
        self._radio = radio_factory(left, theme)
        self._radio.grid(row=0, column=0, sticky="nsew")
        self._radio.launch()

        right = tk.Frame(self, bg=ui.surface, padx=12, pady=10,
                         highlightthickness=1, highlightbackground=ui.border)
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12))
        right.grid_propagate(False)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(4, weight=1)

        heading = tk.Frame(right, bg=ui.surface)
        heading.grid(row=0, column=0, sticky="ew")
        tk.Label(heading, text="↗  TRENDING NOW", bg=ui.surface,
                 fg=ui.accent_primary, font=("Sans", 14, "bold")).pack(side=tk.LEFT)
        self._button(heading, "↻", self.refresh).pack(side=tk.RIGHT)

        tabs = tk.Frame(right, bg=ui.surface)
        tabs.grid(row=1, column=0, sticky="ew")
        self._song_tab = self._button(tabs, "SONGS", lambda: self._change_kind("songs"))
        self._song_tab.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._artist_tab = self._button(tabs, "ARTISTS", lambda: self._change_kind("artists"))
        self._artist_tab.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._paint_kind()
        filters = tk.Frame(right, bg=ui.surface)
        filters.grid(row=2, column=0, sticky="ew", pady=(8, 4))
        self._station_menu = tk.OptionMenu(filters, self._station, "All stations",
                                            command=lambda _: self.refresh())
        self._station_menu.configure(bg=ui.control_background, fg=ui.text,
                                     activebackground=ui.control_active,
                                     activeforeground=ui.text, relief=tk.FLAT,
                                     highlightthickness=0, font=("Sans", 9))
        self._station_menu.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self._period_buttons: dict[str, tk.Button] = {}
        for period, label in (("today", "1D"), ("7d", "7D"), ("30d", "30D")):
            button = self._button(filters, label, lambda p=period: self._change_period(p))
            button.pack(side=tk.LEFT, padx=1)
            self._period_buttons[period] = button
        self._paint_period()

        self._status = tk.Label(right, text="Loading airplay…", bg=ui.surface,
                                fg=ui.text_muted, anchor="w", font=("Sans", 9))
        self._status.grid(row=3, column=0, sticky="ew", pady=(0, 4))

        self._cards = tk.Frame(right, bg=ui.surface)
        self._cards.grid(row=4, column=0, sticky="nsew")
        self._cards.grid_columnconfigure(0, weight=1)
        for index in range(PAGE_SIZE):
            self._cards.grid_rowconfigure(index, weight=1, uniform="songs")

        footer = tk.Frame(right, bg=ui.surface)
        footer.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        self._previous = self._button(footer, "‹ PREV", lambda: self._change_page(-1))
        self._previous.pack(side=tk.LEFT)
        self._page_label = tk.Label(footer, text="0 / 0", bg=ui.surface,
                                    fg=ui.text_muted, font=("Sans", 10, "bold"))
        self._page_label.pack(side=tk.LEFT, expand=True)
        self._next = self._button(footer, "NEXT ›", lambda: self._change_page(1))
        self._next.pack(side=tk.RIGHT)
        actions = tk.Frame(right, bg=ui.surface)
        actions.grid(row=6, column=0, sticky="ew", pady=(8, 0))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        self._play = self._button(actions, "▶ YOUTUBE", self._play_selected)
        self._play.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        self._spotify = self._button(actions, "♫ SPOTIFY", self._open_spotify)
        self._spotify.grid(row=0, column=1, sticky="ew", padx=(3, 0))
        self._render()

    def _button(self, parent: tk.Misc, label: str,
                command: Callable[[], None]) -> tk.Button:
        ui = self._theme.ui
        return tk.Button(parent, text=label, command=command,
                         bg=ui.control_background, fg=ui.text,
                         activebackground=ui.control_active,
                         activeforeground=ui.text, relief=tk.FLAT, bd=0,
                         highlightthickness=0, font=("Sans", 10, "bold"),
                         padx=10, pady=7, cursor="hand2")

    def refresh(self) -> None:
        if not self._online_allowed():
            self.set_error("Offline mode")
            return
        self._status.configure(text="Refreshing airplay charts…")
        self._on_refresh(self._station.get(), self._period.get(), self._kind)

    def set_stations(self, stations: list[dict]) -> None:
        names = ["All stations"] + sorted({s["station"] for s in stations if s.get("station")})
        menu = self._station_menu["menu"]
        menu.delete(0, "end")
        for name in names:
            menu.add_command(label=station_label(name), command=lambda value=name: self._change_station(value))

    def _change_station(self, name: str) -> None:
        self._station.set(name)
        self.refresh()

    def _change_period(self, period: str) -> None:
        self._period.set(period)
        self._paint_period()
        self.refresh()

    def _paint_period(self) -> None:
        ui = self._theme.ui
        for period, button in self._period_buttons.items():
            active = self._period.get() == period
            button.configure(bg=ui.accent_primary if active else ui.control_background,
                             fg=ui.control_text if active else ui.text)

    def set_songs(self, payload: dict) -> None:
        self.set_chart(payload, kind="songs")

    def set_chart(self, payload: dict, *, kind: str) -> None:
        self._kind = kind
        self._paint_kind()
        self._songs = [item for item in payload.get("results", [])
                       if item.get("artist") and (kind == "artists" or item.get("title"))]
        self._selected = None
        self._page = 0
        self._status.configure(text=f'{len(self._songs)} songs  ·  {payload.get("coverage", "unknown")} coverage')
        self._render()

    def network_changed(self) -> None:
        if not self._online_allowed():
            self._songs = []
            self._selected = None
            self._page = 0
            self._status.configure(text="Offline mode: Trending unavailable")
        self._render()

    def set_error(self, message: str) -> None:
        self._status.configure(text=f"MusicForge unavailable: {message}")

    def _change_kind(self, kind: str) -> None:
        if kind == self._kind:
            return
        self._kind = kind
        self._songs = []
        self._selected = None
        self._page = 0
        self._paint_kind()
        self._render()
        self.refresh()

    def _paint_kind(self) -> None:
        ui = self._theme.ui
        for kind, button in (("songs", self._song_tab), ("artists", self._artist_tab)):
            active = kind == self._kind
            button.configure(bg=ui.accent_primary if active else ui.control_background,
                             fg=ui.control_text if active else ui.text)

    def _change_page(self, direction: int) -> None:
        total = max(1, (len(self._songs) + PAGE_SIZE - 1) // PAGE_SIZE)
        self._page = min(total - 1, max(0, self._page + direction))
        self._render()

    def _select(self, song: dict) -> None:
        self._selected = song
        self._render()

    def _render(self) -> None:
        ui = self._theme.ui
        for child in self._cards.winfo_children():
            child.destroy()
        visible = self._songs[self._page * PAGE_SIZE:(self._page + 1) * PAGE_SIZE]
        for index, song in enumerate(visible):
            active = song is self._selected
            bg = ui.control_active if active else ui.surface_alt
            card = tk.Frame(self._cards, bg=bg, padx=8, pady=2,
                            highlightthickness=1,
                            highlightbackground=ui.accent_primary if active else ui.border)
            card.grid(row=index, column=0, sticky="nsew", pady=2)
            card.grid_columnconfigure(1, weight=1)
            rank = tk.Label(card, text=f'{song.get("rank", self._page * PAGE_SIZE + index + 1):02}',
                            bg=bg, fg=ui.accent_primary, font=("Sans", 15, "bold"))
            rank.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))
            title = tk.Label(card, text=song["artist"] if self._kind == "artists" else song["title"], bg=bg, fg=ui.text,
                             anchor="w", font=("Sans", 10, "bold"))
            title.grid(row=0, column=1, sticky="ew")
            title.configure(wraplength=200, justify=tk.LEFT)
            detail = (str(song.get("plays", 0)) + " airplays · " + str(song.get("songs", 0)) + " songs") if self._kind == "artists" else song["artist"]
            artist = tk.Label(card, text=detail, bg=bg, fg=ui.text_muted,
                              anchor="w", font=("Sans", 10))
            artist.grid(row=1, column=1, sticky="ew")
            card.bind("<Configure>", lambda event, label=title: label.configure(
                wraplength=max(80, event.width - 68)))
            for widget in (card, rank, title, artist):
                widget.bind("<Button-1>", lambda _event, item=song: self._select(item))
                widget.configure(cursor="hand2")
        total = max(1, (len(self._songs) + PAGE_SIZE - 1) // PAGE_SIZE)
        self._page_label.configure(text=f"{self._page + 1} / {total}")
        self._previous.configure(state=tk.NORMAL if self._page > 0 else tk.DISABLED)
        self._next.configure(state=tk.NORMAL if self._page + 1 < total else tk.DISABLED)
        self._play.configure(state=tk.NORMAL if self._online_allowed() and self._selected is not None and self._kind == "songs" else tk.DISABLED)
        self._spotify.configure(state=tk.NORMAL if self._online_allowed() and self._selected is not None and self._kind == "songs" else tk.DISABLED)

    def _restore_fm(self) -> None:
        if self._spotify_pane is not None:
            self._spotify_pane.destroy()
            self._spotify_pane = None
        if self._video_pane is not None:
            self._video_pane.destroy()
            self._video_pane = None
        self._radio = self._radio_factory(self._left, self._theme)
        self._radio.grid(row=0, column=0, sticky="nsew")
        self._radio.launch()

    def _open_spotify(self) -> None:
        if not self._online_allowed():
            self._status.configure(text="Offline mode: Spotify unavailable")
            return
        if self._selected is None or self._spotify_factory is None:
            self._status.configure(text="Spotify panel unavailable")
            return
        if self._video_pane is not None:
            self._video_pane.destroy()
            self._video_pane = None
        elif self._spotify_pane is None:
            self._radio.destroy()
        if self._spotify_pane is not None:
            self._spotify_pane.destroy()
        self._spotify_pane = self._spotify_factory(self._left, self._restore_fm, self._selected["artist"], self._selected["title"])
        self._spotify_pane.grid(row=0, column=0, sticky="nsew")

    def _play_selected(self) -> None:
        if not self._online_allowed():
            self._status.configure(text="Offline mode: YouTube unavailable")
            return
        if self._selected is None:
            return
        request = SongLaunchRequest(
            title=self._selected["title"], artist=self._selected["artist"],
            destination=SongDestination.YOUTUBE)
        player = self._video_player()
        if player is None:
            self._on_play(request)
            return
        # Retire the SDR session before starting browser audio.
        if self._video_pane is not None:
            self._video_pane.destroy()
            self._video_pane = None
        elif self._spotify_pane is not None:
            self._spotify_pane.destroy()
            self._spotify_pane = None
        else:
            self._radio.destroy()
        self._video_pane = TrendingVideoPane(
            self._left, query=request.search_text,
            play=player.play, stop=player.stop,
            on_back=self._restore_fm, window_class="openroadcode-youtube",
            background=self._theme.ui.background,
            foreground=self._theme.ui.text)
        self._video_pane.grid(row=0, column=0, sticky="nsew")
