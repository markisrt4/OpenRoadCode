# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Pair the existing SDR radio player with MusicForge airplay charts."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from ui.media.song_launch import SongDestination, SongLaunchRequest
from ui.theme import ThemeBundle


class TrendingRadioPanel(tk.Frame):
    """Present the existing SDR player beside a selectable airplay chart."""

    def __init__(self, parent: tk.Misc, *, theme: ThemeBundle,
                 on_back: Callable[[], None],
                 on_refresh: Callable[[str, str], None],
                 on_play: Callable[[SongLaunchRequest], None],
                 radio_factory: Callable[[tk.Misc, ThemeBundle], tk.Widget]) -> None:
        ui = theme.ui
        super().__init__(parent, bg=ui.background)
        self._on_refresh = on_refresh
        self._on_play = on_play
        self._songs: list[dict] = []
        self._selected: dict | None = None
        self._station = tk.StringVar(value="All stations")
        self._period = tk.StringVar(value="7d")
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        header = tk.Frame(self, bg=ui.background)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=8)
        tk.Button(header, text="‹ RADIO", command=on_back).pack(side=tk.LEFT)
        tk.Label(header, text="TRENDING  ·  MUSICFORGE", bg=ui.background,
                 fg=ui.text, font=("Sans", 15, "bold")).pack(side=tk.LEFT, padx=16)

        left = tk.Frame(self, bg=ui.background)
        left.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(0, 12))
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)
        self._radio = radio_factory(left, theme)
        self._radio.grid(row=0, column=0, sticky="nsew")
        self._radio.launch()

        right = tk.Frame(self, bg=ui.surface, padx=12, pady=12)
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12))
        tk.Label(right, text="TRENDING NOW", bg=ui.surface, fg=ui.text,
                 font=("Sans", 14, "bold")).pack(anchor="w")
        controls = tk.Frame(right, bg=ui.surface)
        controls.pack(fill=tk.X, pady=8)
        self._station_menu = tk.OptionMenu(controls, self._station, "All stations",
                                            command=lambda _: self.refresh())
        self._station_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.OptionMenu(controls, self._period, "today", "7d", "30d",
                      command=lambda _: self.refresh()).pack(side=tk.LEFT)
        tk.Button(controls, text="↻", command=self.refresh).pack(side=tk.LEFT)
        self._play = tk.Button(right, text="SEARCH SELECTED ON YOUTUBE  ▶",
                               state=tk.DISABLED, command=self._play_selected)
        self._play.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))
        self._status = tk.Label(right, text="Loading airplay…", bg=ui.surface,
                                fg=ui.text_muted, anchor="w")
        self._status.pack(fill=tk.X)
        listing = tk.Frame(right, bg=ui.surface)
        listing.pack(fill=tk.BOTH, expand=True)
        self._list = tk.Listbox(listing, bg=ui.control_background, fg=ui.text,
                                selectbackground=ui.accent_primary, font=("Sans", 11),
                                relief=tk.FLAT, exportselection=False)
        self._list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = tk.Scrollbar(listing, command=self._list.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._list.configure(yscrollcommand=scroll.set)
        self._list.bind("<<ListboxSelect>>", self._choose)

    def refresh(self) -> None:
        self._status.configure(text="Loading airplay…")
        self._on_refresh(self._station.get(), self._period.get())

    def set_stations(self, stations: list[dict]) -> None:
        names = ["All stations"] + sorted({s["station"] for s in stations if s.get("station")})
        menu = self._station_menu["menu"]
        menu.delete(0, "end")
        for name in names:
            menu.add_command(label=name, command=lambda value=name: self._change_station(value))

    def _change_station(self, name: str) -> None:
        self._station.set(name)
        self.refresh()

    def set_songs(self, payload: dict) -> None:
        self._songs = [s for s in payload.get("results", [])
                       if s.get("artist") and s.get("title")]
        self._selected = None
        self._play.configure(state=tk.DISABLED)
        self._list.delete(0, tk.END)
        for song in self._songs:
            self._list.insert(tk.END, f'{song.get("rank", "")}. {song["artist"]} · {song["title"]}')
        coverage = payload.get("coverage", "unknown")
        self._status.configure(text=f'{len(self._songs)} songs · {coverage} airplay coverage')

    def set_error(self, message: str) -> None:
        self._status.configure(text=f"MusicForge unavailable: {message}")

    def _choose(self, _event: object) -> None:
        selected = self._list.curselection()
        if not selected:
            return
        self._selected = self._songs[selected[0]]
        self._play.configure(state=tk.NORMAL)

    def _play_selected(self) -> None:
        if self._selected is not None:
            self._on_play(SongLaunchRequest(
                title=self._selected["title"], artist=self._selected["artist"],
                destination=SongDestination.YOUTUBE))
