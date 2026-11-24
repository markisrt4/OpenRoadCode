# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Build Tk station cards and streaming-radio controls."""

from __future__ import annotations

import tkinter as tk
from functools import partial
from typing import TYPE_CHECKING

from ui.radio.streaming_radio_types import StreamingRadioStation
from ui.radio.station_filters import (
    BAND_FILTERS,
    GENRE_FILTERS,
    QUALITY_FILTERS,
    is_explicit_internet_only,
)

if TYPE_CHECKING:
    from .streaming_radio_panel import StreamingRadioPanel

BG = "#05090d"
PANEL = "#0b1117"
CARD = "#101820"
CARD_SELECTED = "#17232d"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#84ce1f"
BLUE = "#168bd1"
DANGER = "#f15a16"


def build_streaming_header(self: StreamingRadioPanel) -> None:
    header = tk.Frame(self, bg=BG)
    header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
    header.grid_columnconfigure(0, weight=1)
    tk.Label(header, text="STREAMING RADIO", bg=BG, fg=BLUE, font=("Sans", 18, "bold")).grid(
        row=0, column=0, sticky="w"
    )
    tk.Button(
        header,
        text="‹ BACK",
        command=self._on_back,
        bg=PANEL,
        fg=TEXT,
        activebackground=CARD_SELECTED,
        activeforeground=BLUE,
        relief=tk.FLAT,
        bd=0,
        font=("Sans", 14, "bold"),
        padx=14,
        pady=7,
        highlightthickness=0,
    ).grid(row=0, column=1, sticky="e")


def build_filter_drawer(self: StreamingRadioPanel) -> None:
    drawer = tk.Frame(self, bg=PANEL, highlightthickness=2, highlightbackground=BORDER)
    self._filter_drawer = drawer
    drawer.grid_columnconfigure(0, weight=1)
    header = tk.Frame(drawer, bg=CARD)
    header.grid(row=0, column=0, sticky="ew")
    header.grid_columnconfigure(0, weight=1)
    tk.Label(
        header,
        text="STATION FILTERS",
        bg=CARD,
        fg=TEXT,
        font=("Sans", 15, "bold"),
        anchor="w",
        padx=12,
        pady=11,
    ).grid(row=0, column=0, sticky="ew")
    tk.Button(
        header,
        text="✕",
        command=self._close_filter_drawer,
        bg=CARD,
        fg=MUTED,
        activebackground=CARD_SELECTED,
        activeforeground=TEXT,
        relief=tk.FLAT,
        bd=0,
        font=("Sans", 15, "bold"),
        padx=12,
        pady=8,
        highlightthickness=0,
    ).grid(row=0, column=1)
    body = tk.Frame(drawer, bg=PANEL, padx=12, pady=10)
    body.grid(row=1, column=0, sticky="nsew")
    body.grid_columnconfigure(0, weight=1, uniform="filter-drawer")
    body.grid_columnconfigure(1, weight=1, uniform="filter-drawer")
    self._build_filter_group(
        body, row=0, column=0, title="MUSIC / CONTENT", key="genre", values=GENRE_FILTERS
    )
    self._build_filter_group(
        body,
        row=0,
        column=1,
        title="STREAM QUALITY",
        key="quality",
        values=QUALITY_FILTERS,
        helper="Low <96   Mid 96–191   High ≥192 kbps",
    )
    self._build_filter_group(
        body,
        row=1,
        column=1,
        title="BAND / ORIGIN",
        key="band",
        values=BAND_FILTERS,
        helper="Internet-only lives here; broadcast band is best-effort metadata.",
    )
    tk.Button(
        body,
        text="CLEAR FILTERS",
        command=self._clear_station_filters,
        bg=CARD,
        fg=TEXT,
        activebackground=CARD_SELECTED,
        activeforeground=GREEN,
        relief=tk.FLAT,
        bd=0,
        font=("Sans", 15, "bold"),
        pady=8,
        highlightthickness=0,
    ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 4))


def build_filter_group(
    self: StreamingRadioPanel,
    parent: tk.Misc,
    *,
    row: int,
    column: int,
    title: str,
    key: str,
    values: tuple[str, ...],
    helper: str | None = None,
) -> None:
    group = tk.Frame(parent, bg=PANEL)
    group.grid(
        row=row,
        column=column,
        sticky="new",
        padx=(0, 6) if column == 0 else (6, 0),
        pady=(0, 10),
    )
    group.grid_columnconfigure(0, weight=1)
    tk.Label(group, text=title, bg=PANEL, fg=BLUE, font=("Sans", 15, "bold"), anchor="w").grid(
        row=0, column=0, sticky="ew"
    )
    current = {
        "genre": self._genre_filter,
        "quality": self._quality_filter,
        "band": self._band_filter,
    }[key]
    value_label = tk.Label(
        group,
        text=current,
        bg=PANEL,
        fg=GREEN if current != "All" else MUTED,
        font=("Sans", 15, "bold"),
        anchor="e",
    )
    value_label.grid(row=0, column=1, sticky="e")
    self._filter_value_labels[key] = value_label
    choices = tk.Frame(group, bg=PANEL)
    choices.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))
    columns = 2 if len(values) <= 6 else 3
    for choice_column in range(columns):
        choices.grid_columnconfigure(choice_column, weight=1)
    for index, value in enumerate(values):
        tk.Button(
            choices,
            text=value.upper(),
            command=partial(self._set_station_filter, key, value),
            bg=CARD,
            fg=TEXT,
            activebackground=CARD_SELECTED,
            activeforeground=GREEN,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 14, "bold"),
            padx=5,
            pady=6,
            highlightthickness=0,
        ).grid(
            row=index // columns,
            column=index % columns,
            sticky="ew",
            padx=2,
            pady=2,
            highlightthickness=0,
        )
    if helper:
        tk.Label(
            group,
            text=helper,
            bg=PANEL,
            fg=MUTED,
            font=("Sans", 14),
            anchor="w",
            justify=tk.LEFT,
            wraplength=220,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))


def build_station_card(
    self: StreamingRadioPanel, station: StreamingRadioStation, *, row: int, column: int
) -> None:
    selected = (
        self._selected_station is not None
        and station.station_id == self._selected_station.station_id
    )
    current = self._playback.station
    playing = (
        current is not None
        and current.station_id == station.station_id
        and self._playback.is_playing
    )
    card_bg = "#142619" if playing else CARD_SELECTED if selected else CARD
    border = GREEN if playing else BLUE if selected else BORDER
    thickness = 3 if playing else 1
    card = tk.Frame(
        self._list, bg=card_bg, highlightthickness=thickness, highlightbackground=border
    )
    card.grid(row=row, column=column, sticky="nsew", padx=5, pady=5)
    card.grid_columnconfigure(1, weight=1)
    if playing:
        banner = tk.Label(
            card,
            text="●  NOW PLAYING",
            bg=GREEN,
            fg="#071006",
            font=("Sans", 15, "bold"),
            anchor="w",
            padx=8,
            pady=3,
        )
        banner.grid(row=0, column=0, columnspan=3, sticky="ew")
        content_row = 1
    else:
        banner = None
        content_row = 0
    artwork = tk.Label(
        card, text="RADIO", bg="#081018", fg=MUTED, width=8, height=4, font=("Sans", 14, "bold")
    )
    artwork.grid(row=content_row, column=0, rowspan=3, padx=(8, 7), pady=8, sticky="w")
    self._apply_or_load_artwork(station, artwork)
    name = tk.Label(
        card,
        text=station.name,
        bg=card_bg,
        fg=GREEN if playing else TEXT,
        font=("Sans", 14 if playing else 11, "bold"),
        anchor="w",
        justify=tk.LEFT,
        wraplength=250,
    )
    name.grid(row=content_row, column=1, columnspan=2, sticky="ew", padx=(0, 6), pady=(8, 1))
    details = _station_details(station)
    if is_explicit_internet_only(station):
        details = f"INTERNET ONLY • {details}"
    detail_label = tk.Label(
        card,
        text=details,
        bg=card_bg,
        fg=BLUE if is_explicit_internet_only(station) else MUTED,
        font=("Sans", 14),
        anchor="w",
        justify=tk.LEFT,
        wraplength=245,
    )
    detail_label.grid(
        row=content_row + 1, column=1, columnspan=2, sticky="ew", padx=(0, 6), pady=(0, 4)
    )
    favorite = station.station_id in self._favorites
    favorite_button = tk.Button(
        card,
        text="★" if favorite else "☆",
        command=partial(self._toggle_station_favorite, station),
        bg=card_bg,
        fg=GREEN if favorite else MUTED,
        activebackground=card_bg,
        activeforeground=GREEN,
        relief=tk.FLAT,
        bd=0,
        font=("Sans", 15),
        padx=5,
        pady=2,
        highlightthickness=0,
    )
    favorite_button.grid(row=content_row + 2, column=1, sticky="w", pady=(0, 6))
    play_button = tk.Button(
        card,
        text="■  STOP" if playing else "▶ PLAY",
        command=self._request_stop if playing else partial(self._request_play, station),
        state=tk.DISABLED if self._playback_busy else tk.NORMAL,
        bg=GREEN if playing else PANEL,
        fg="#071006" if playing else TEXT,
        activebackground="#9bdc45" if playing else CARD_SELECTED,
        activeforeground="#071006" if playing else GREEN,
        disabledforeground=MUTED,
        relief=tk.FLAT,
        bd=0,
        font=("Sans", 11 if playing else 9, "bold"),
        padx=14,
        pady=7 if playing else 5,
        highlightthickness=0,
    )
    play_button.grid(row=content_row + 2, column=2, sticky="e", padx=(4, 7), pady=(0, 6))
    clickable = [card, artwork, name, detail_label]
    if banner is not None:
        clickable.append(banner)
    for widget in clickable:
        widget.bind("<Button-1>", lambda _event: self._select_station(station))


def _station_details(station: StreamingRadioStation) -> str:
    details: list[str] = []
    if station.state:
        details.append(station.state)
    if station.codec:
        details.append(station.codec)
    if station.bitrate_kbps is not None:
        details.append(f"{station.bitrate_kbps} kbps")
    if station.tags:
        details.extend(station.tags[:2])
    return " • ".join(details) or "Streaming station"
