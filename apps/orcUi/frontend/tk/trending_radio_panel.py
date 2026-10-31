# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Touch-friendly FM radio and MusicForge airplay split screen."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from ui.media.song_launch import SongDestination, SongLaunchRequest
from ui.radio.station_identity import station_label
from ui.theme import ThemeBundle

PAGE_SIZE = 4


class TrendingRadioPanel(tk.Frame):
    """Keep real FM controls beside paged airplay cards, without scrollbars."""

    def __init__(self, parent: tk.Misc, *, theme: ThemeBundle,
                 on_back: Callable[[], None],
                 on_refresh: Callable[[str, str], None],
                 on_play: Callable[[SongLaunchRequest], None],
                 radio_factory: Callable[[tk.Misc, ThemeBundle], tk.Widget]) -> None:
        ui = theme.ui
        super().__init__(parent, bg=ui.background)
        self._theme = theme
        self._on_refresh = on_refresh
        self._on_play = on_play
        self._songs: list[dict] = []
        self._selected: dict | None = None
        self._page = 0
        self._station = tk.StringVar(value="All stations")
        self._period = tk.StringVar(value="7d")
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
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
        self._radio = radio_factory(left, theme)
        self._radio.grid(row=0, column=0, sticky="nsew")
        self._radio.launch()

        right = tk.Frame(self, bg=ui.surface, padx=12, pady=10,
                         highlightthickness=1, highlightbackground=ui.border)
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(3, weight=1)

        heading = tk.Frame(right, bg=ui.surface)
        heading.grid(row=0, column=0, sticky="ew")
        tk.Label(heading, text="↗  TRENDING NOW", bg=ui.surface,
                 fg=ui.accent_primary, font=("Sans", 14, "bold")).pack(side=tk.LEFT)
        self._button(heading, "↻", self.refresh).pack(side=tk.RIGHT)

        filters = tk.Frame(right, bg=ui.surface)
        filters.grid(row=1, column=0, sticky="ew", pady=(8, 4))
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
        self._status.grid(row=2, column=0, sticky="ew", pady=(0, 4))

        self._cards = tk.Frame(right, bg=ui.surface)
        self._cards.grid(row=3, column=0, sticky="nsew")
        self._cards.grid_columnconfigure(0, weight=1)
        for index in range(PAGE_SIZE):
            self._cards.grid_rowconfigure(index, weight=1, uniform="songs")

        footer = tk.Frame(right, bg=ui.surface)
        footer.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self._previous = self._button(footer, "‹ PREV", lambda: self._change_page(-1))
        self._previous.pack(side=tk.LEFT)
        self._page_label = tk.Label(footer, text="0 / 0", bg=ui.surface,
                                    fg=ui.text_muted, font=("Sans", 10, "bold"))
        self._page_label.pack(side=tk.LEFT, expand=True)
        self._next = self._button(footer, "NEXT ›", lambda: self._change_page(1))
        self._next.pack(side=tk.RIGHT)
        self._play = self._button(right, "▶  SEARCH SELECTED ON YOUTUBE",
                                  self._play_selected)
        self._play.grid(row=5, column=0, sticky="ew", pady=(8, 0))
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
        self._status.configure(text="Refreshing airplay charts…")
        self._on_refresh(self._station.get(), self._period.get())

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
        self._songs = [song for song in payload.get("results", [])
                       if song.get("artist") and song.get("title")]
        self._selected = None
        self._page = 0
        self._status.configure(text=f'{len(self._songs)} songs  ·  {payload.get("coverage", "unknown")} coverage')
        self._render()

    def set_error(self, message: str) -> None:
        self._status.configure(text=f"MusicForge unavailable: {message}")

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
            title = tk.Label(card, text=song["title"], bg=bg, fg=ui.text,
                             anchor="w", font=("Sans", 10, "bold"))
            title.grid(row=0, column=1, sticky="ew")
            title.configure(wraplength=200, justify=tk.LEFT)
            artist = tk.Label(card, text=song["artist"], bg=bg, fg=ui.text_muted,
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
        self._play.configure(state=tk.NORMAL if self._selected is not None else tk.DISABLED)

    def _play_selected(self) -> None:
        if self._selected is not None:
            self._on_play(SongLaunchRequest(
                title=self._selected["title"], artist=self._selected["artist"],
                destination=SongDestination.YOUTUBE))
