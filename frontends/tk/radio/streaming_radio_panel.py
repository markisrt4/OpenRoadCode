# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Touch-oriented streaming-radio browser for the ORC radio screen."""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable

from controllers.radio.streaming_radio_directory_if import StreamingRadioDirectoryIf
from controllers.radio.streaming_radio_types import StreamingRadioStation


BG = "#05090d"
PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#84ce1f"
BLUE = "#168bd1"
DANGER = "#f15a16"

DETROIT_LATITUDE = 42.3314
DETROIT_LONGITUDE = -83.0458
DETROIT_RADIUS_KM = 80.0


BackHandler = Callable[[], None]
StationHandler = Callable[[StreamingRadioStation], None]


class StreamingRadioPanel(tk.Frame):
    """Browse local/regional streaming stations without owning playback policy."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        directory: StreamingRadioDirectoryIf,
        on_back: BackHandler,
        on_station_selected: StationHandler | None = None,
    ) -> None:
        super().__init__(parent, bg=BG)
        self._directory = directory
        self._on_back = on_back
        self._on_station_selected = on_station_selected
        self._mode = "local"
        self._include_internet_only = False
        self._favorites: set[str] = set()
        self._stations: tuple[StreamingRadioStation, ...] = ()
        self._selected_station: StreamingRadioStation | None = None
        self._load_generation = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_filters()
        self._build_station_list()
        self._build_footer()
        self.after_idle(self._reload)

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def include_internet_only(self) -> bool:
        return self._include_internet_only

    @property
    def favorite_station_ids(self) -> frozenset[str]:
        return frozenset(self._favorites)

    @property
    def selected_station(self) -> StreamingRadioStation | None:
        return self._selected_station

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=BG)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(
            header,
            text="STREAMING RADIO",
            bg=BG,
            fg=BLUE,
            font=("Sans", 18, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Button(
            header,
            text="‹ BACK",
            command=self._on_back,
            bg=PANEL,
            fg=TEXT,
            activebackground="#17232d",
            activeforeground=BLUE,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 10, "bold"),
            padx=14,
            pady=7,
        ).grid(row=0, column=1, sticky="e")

    def _build_filters(self) -> None:
        filters = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        filters.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        for column in range(4):
            filters.grid_columnconfigure(column, weight=1)

        self._mode_buttons: dict[str, tk.Button] = {}
        for column, (mode, label) in enumerate(
            (("local", "LOCAL"), ("regional", "REGIONAL"), ("favorites", "★ FAVORITES"))
        ):
            button = tk.Button(
                filters,
                text=label,
                command=lambda selected=mode: self._set_mode(selected),
                bg=PANEL,
                fg=TEXT,
                activebackground="#17232d",
                activeforeground=GREEN,
                relief=tk.FLAT,
                bd=0,
                font=("Sans", 10, "bold"),
                padx=10,
                pady=8,
            )
            button.grid(row=0, column=column, sticky="ew")
            self._mode_buttons[mode] = button

        self._internet_button = tk.Button(
            filters,
            text="INCLUDE INTERNET-ONLY: OFF",
            command=self._toggle_internet_only,
            bg=PANEL,
            fg=MUTED,
            activebackground="#17232d",
            activeforeground=BLUE,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 9, "bold"),
            padx=10,
            pady=8,
        )
        self._internet_button.grid(row=0, column=3, sticky="ew")
        self._paint_filters()

    def _build_station_list(self) -> None:
        host = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        host.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 6))
        host.grid_columnconfigure(0, weight=1)
        host.grid_rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(host, bg=PANEL, highlightthickness=0, bd=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(host, orient=tk.VERTICAL, command=self._canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=scrollbar.set)

        self._list = tk.Frame(self._canvas, bg=PANEL)
        self._list_window = self._canvas.create_window((0, 0), window=self._list, anchor="nw")
        self._list.bind("<Configure>", self._on_list_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        self._status = tk.Label(
            self._list,
            text="Loading local stations…",
            bg=PANEL,
            fg=MUTED,
            font=("Sans", 12),
            pady=30,
        )
        self._status.pack(fill=tk.X)

    def _build_footer(self) -> None:
        footer = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))
        footer.grid_columnconfigure(0, weight=1)
        self._selection_label = tk.Label(
            footer,
            text="Select a station",
            bg=PANEL,
            fg=MUTED,
            font=("Sans", 11, "bold"),
            anchor="w",
            padx=12,
            pady=9,
        )
        self._selection_label.grid(row=0, column=0, sticky="ew")
        self._favorite_button = tk.Button(
            footer,
            text="☆ FAVORITE",
            command=self._toggle_favorite,
            state=tk.DISABLED,
            bg=PANEL,
            fg=TEXT,
            activebackground="#17232d",
            activeforeground=GREEN,
            disabledforeground=MUTED,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 10, "bold"),
            padx=14,
            pady=9,
        )
        self._favorite_button.grid(row=0, column=1, sticky="e")

    def _set_mode(self, mode: str) -> None:
        if mode not in self._mode_buttons or mode == self._mode:
            return
        self._mode = mode
        self._paint_filters()
        if mode == "favorites":
            self._render_stations()
        else:
            self._reload()

    def _toggle_internet_only(self) -> None:
        self._include_internet_only = not self._include_internet_only
        self._paint_filters()
        self._render_stations()

    def _paint_filters(self) -> None:
        for mode, button in self._mode_buttons.items():
            active = mode == self._mode
            button.configure(fg=GREEN if active else TEXT, bg="#101820" if active else PANEL)
        state = "ON" if self._include_internet_only else "OFF"
        self._internet_button.configure(
            text=f"INCLUDE INTERNET-ONLY: {state}",
            fg=BLUE if self._include_internet_only else MUTED,
            bg="#101820" if self._include_internet_only else PANEL,
        )

    def _reload(self) -> None:
        if self._mode == "favorites":
            self._render_stations()
            return
        self._load_generation += 1
        generation = self._load_generation
        self._show_status("Loading local stations…" if self._mode == "local" else "Loading Michigan stations…")
        threading.Thread(
            target=self._load_worker,
            args=(generation, self._mode),
            name="orcui-streaming-radio-directory",
            daemon=True,
        ).start()

    def _load_worker(self, generation: int, mode: str) -> None:
        try:
            if mode == "local":
                stations = self._directory.stations_near(
                    latitude=DETROIT_LATITUDE,
                    longitude=DETROIT_LONGITUDE,
                    radius_km=DETROIT_RADIUS_KM,
                    state="Michigan",
                    country_code="US",
                    limit=50,
                )
            else:
                stations = self._directory.stations_by_region(
                    state="Michigan",
                    country_code="US",
                    limit=100,
                )
        except Exception as error:
            self.after(0, lambda: self._finish_load(generation, (), error))
            return
        self.after(0, lambda: self._finish_load(generation, stations, None))

    def _finish_load(
        self,
        generation: int,
        stations: tuple[StreamingRadioStation, ...],
        error: Exception | None,
    ) -> None:
        if generation != self._load_generation or not self.winfo_exists():
            return
        if error is not None:
            self._stations = ()
            self._show_status(f"Unable to load stations: {type(error).__name__}: {error}", danger=True)
            return
        self._stations = stations
        self._render_stations()

    def _render_stations(self) -> None:
        for child in self._list.winfo_children():
            child.destroy()

        stations = self._visible_stations()
        if not stations:
            message = "No favorite stations yet." if self._mode == "favorites" else "No stations found."
            self._show_status(message)
            return

        for station in stations:
            self._build_station_row(station)

    def _visible_stations(self) -> tuple[StreamingRadioStation, ...]:
        stations = self._stations
        if self._mode == "favorites":
            stations = tuple(station for station in stations if station.station_id in self._favorites)
        if not self._include_internet_only:
            stations = tuple(station for station in stations if not is_explicit_internet_only(station))
        return stations

    def _build_station_row(self, station: StreamingRadioStation) -> None:
        selected = self._selected_station is not None and station.station_id == self._selected_station.station_id
        row_bg = "#101820" if selected else PANEL
        row = tk.Frame(self._list, bg=row_bg, highlightthickness=1, highlightbackground=BORDER)
        row.pack(fill=tk.X, padx=5, pady=3)
        row.grid_columnconfigure(1, weight=1)

        favorite = "★" if station.station_id in self._favorites else "☆"
        tk.Label(row, text=favorite, bg=row_bg, fg=GREEN if favorite == "★" else MUTED, font=("Sans", 14)).grid(
            row=0, column=0, rowspan=2, padx=(10, 8), pady=8
        )
        tk.Label(row, text=station.name, bg=row_bg, fg=TEXT, font=("Sans", 12, "bold"), anchor="w").grid(
            row=0, column=1, sticky="ew", pady=(7, 0)
        )
        tk.Label(
            row,
            text=_station_details(station),
            bg=row_bg,
            fg=MUTED,
            font=("Sans", 9),
            anchor="w",
        ).grid(row=1, column=1, sticky="ew", pady=(0, 7))
        if is_explicit_internet_only(station):
            tk.Label(row, text="INTERNET ONLY", bg=row_bg, fg=BLUE, font=("Sans", 8, "bold"), padx=10).grid(
                row=0, column=2, rowspan=2, sticky="e"
            )

        for widget in (row, *row.winfo_children()):
            widget.bind("<Button-1>", lambda _event, item=station: self._select_station(item))

    def _select_station(self, station: StreamingRadioStation) -> None:
        self._selected_station = station
        self._selection_label.configure(text=station.name, fg=TEXT)
        self._favorite_button.configure(state=tk.NORMAL)
        self._paint_favorite_button()
        self._render_stations()
        if self._on_station_selected is not None:
            self._on_station_selected(station)

    def _toggle_favorite(self) -> None:
        station = self._selected_station
        if station is None:
            return
        if station.station_id in self._favorites:
            self._favorites.remove(station.station_id)
        else:
            self._favorites.add(station.station_id)
        self._paint_favorite_button()
        self._render_stations()

    def _paint_favorite_button(self) -> None:
        station = self._selected_station
        is_favorite = station is not None and station.station_id in self._favorites
        self._favorite_button.configure(
            text="★ FAVORITE" if is_favorite else "☆ FAVORITE",
            fg=GREEN if is_favorite else TEXT,
        )

    def _show_status(self, text: str, *, danger: bool = False) -> None:
        for child in self._list.winfo_children():
            child.destroy()
        tk.Label(
            self._list,
            text=text,
            bg=PANEL,
            fg=DANGER if danger else MUTED,
            font=("Sans", 11),
            pady=30,
        ).pack(fill=tk.X)

    def _on_list_configure(self, _event: tk.Event[tk.Misc]) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event[tk.Misc]) -> None:
        self._canvas.itemconfigure(self._list_window, width=event.width)


def is_explicit_internet_only(station: StreamingRadioStation) -> bool:
    """Conservatively identify stations explicitly tagged as internet/web-only."""
    tags = {tag.casefold().replace("_", " ").replace("-", " ") for tag in station.tags}
    return bool(tags & {"internet", "internet only", "online only", "web radio", "webradio"})


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
