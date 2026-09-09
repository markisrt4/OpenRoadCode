# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Touch-oriented streaming-radio browser for the ORC radio screen."""

from __future__ import annotations

import re
import threading
import tkinter as tk
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from urllib.request import Request, urlopen

from PIL import Image, ImageOps, ImageTk

from controllers.radio.streaming_radio_controller import StreamingRadioController
from controllers.radio.streaming_radio_directory_if import StreamingRadioDirectoryIf
from controllers.radio.streaming_radio_types import StreamingRadioStation

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

DETROIT_LATITUDE = 42.3314
DETROIT_LONGITUDE = -83.0458
DETROIT_RADIUS_KM = 80.0
ARTWORK_SIZE = 64
ARTWORK_TIMEOUT_S = 5.0
ARTWORK_USER_AGENT = "OpenRoadCode/streaming-radio"
CARD_COLUMNS = 2

GENRE_FILTERS = (
    "All", "Rock", "Country", "Pop", "News/Talk", "Sports", "Jazz",
    "Classical", "Christian", "Hip-Hop/R&B", "Electronic", "Variety",
)
QUALITY_FILTERS = ("All", "Low", "Mid", "High")
BAND_FILTERS = ("All", "FM", "AM", "DAB", "Internet-only", "Unknown")

_GENRE_TAGS = {
    "Rock": {"rock", "classic rock", "alternative rock", "indie rock", "hard rock"},
    "Country": {"country", "americana", "bluegrass"},
    "Pop": {"pop", "top 40", "top40", "adult contemporary", "hot ac"},
    "News/Talk": {"news", "talk", "talk radio", "public radio", "politics"},
    "Sports": {"sports", "sport", "sports talk"},
    "Jazz": {"jazz", "smooth jazz"},
    "Classical": {"classical", "opera"},
    "Christian": {"christian", "christian contemporary", "gospel", "religious", "worship"},
    "Hip-Hop/R&B": {"hip hop", "hip-hop", "rap", "r&b", "rnb", "urban"},
    "Electronic": {"electronic", "edm", "dance", "house", "techno", "trance"},
    "Variety": {"variety", "eclectic", "mixed", "community"},
}

BackHandler = Callable[[], None]
StationHandler = Callable[[StreamingRadioStation], None]


class StreamingRadioPanel(tk.Frame):
    """Browse and play local/regional streaming radio stations."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        directory: StreamingRadioDirectoryIf,
        controller: StreamingRadioController,
        on_back: BackHandler,
        on_station_selected: StationHandler | None = None,
    ) -> None:
        super().__init__(parent, bg=BG)
        self._directory = directory
        self._controller = controller
        self._on_back = on_back
        self._on_station_selected = on_station_selected
        self._mode = "local"
        self._internet_only = False
        self._favorites: set[str] = set()
        self._stations: tuple[StreamingRadioStation, ...] = ()
        self._selected_station: StreamingRadioStation | None = None
        self._load_generation = 0
        self._playback_busy = False
        self._genre_filter = "All"
        self._quality_filter = "All"
        self._band_filter = "All"
        self._filter_drawer_open = False
        self._filter_drawer: tk.Frame | None = None
        self._filter_value_labels: dict[str, tk.Label] = {}
        self._artwork_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="orcui-radio-artwork")
        self._artwork_images: dict[str, ImageTk.PhotoImage] = {}
        self._artwork_pending: set[str] = set()

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
        return self._internet_only

    @property
    def internet_only(self) -> bool:
        return self._internet_only

    @property
    def favorite_station_ids(self) -> frozenset[str]:
        return frozenset(self._favorites)

    @property
    def selected_station(self) -> StreamingRadioStation | None:
        return self._selected_station

    def destroy(self) -> None:
        self._artwork_executor.shutdown(wait=False, cancel_futures=True)
        super().destroy()

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=BG)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(header, text="STREAMING RADIO", bg=BG, fg=BLUE, font=("Sans", 18, "bold")).grid(row=0, column=0, sticky="w")
        tk.Button(header, text="‹ BACK", command=self._on_back, bg=PANEL, fg=TEXT, activebackground=CARD_SELECTED, activeforeground=BLUE, relief=tk.FLAT, bd=0, font=("Sans", 10, "bold"), padx=14, pady=7).grid(row=0, column=1, sticky="e")

    def _build_filters(self) -> None:
        filters = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        filters.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        for column in range(4):
            filters.grid_columnconfigure(column, weight=1)
        self._mode_buttons: dict[str, tk.Button] = {}
        for column, (mode, label) in enumerate((("local", "LOCAL"), ("regional", "REGIONAL"), ("favorites", "★ FAVORITES"))):
            button = tk.Button(filters, text=label, command=lambda selected=mode: self._set_mode(selected), bg=PANEL, fg=TEXT, activebackground=CARD_SELECTED, activeforeground=GREEN, relief=tk.FLAT, bd=0, font=("Sans", 10, "bold"), padx=10, pady=8)
            button.grid(row=0, column=column, sticky="ew")
            self._mode_buttons[mode] = button
        self._filters_button = tk.Button(filters, text="☰ FILTERS", command=self._toggle_filter_drawer, bg=PANEL, fg=TEXT, activebackground=CARD_SELECTED, activeforeground=GREEN, relief=tk.FLAT, bd=0, font=("Sans", 9, "bold"), padx=8, pady=8)
        self._filters_button.grid(row=0, column=3, sticky="ew")
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
        for column in range(CARD_COLUMNS):
            self._list.grid_columnconfigure(column, weight=1, uniform="streaming-card")
        self._list_window = self._canvas.create_window((0, 0), window=self._list, anchor="nw")
        self._list.bind("<Configure>", self._on_list_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._show_status("Loading local stations…")

    def _build_footer(self) -> None:
        footer = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))
        footer.grid_columnconfigure(0, weight=1)
        self._selection_label = tk.Label(footer, text="Select a station", bg=PANEL, fg=MUTED, font=("Sans", 10, "bold"), anchor="w", padx=12, pady=8)
        self._selection_label.grid(row=0, column=0, sticky="ew")
        self._stop_button = tk.Button(footer, text="■ STOP", command=self._request_stop, state=tk.NORMAL if self._controller.is_playing else tk.DISABLED, bg=PANEL, fg=TEXT, activebackground=CARD_SELECTED, activeforeground=DANGER, disabledforeground=MUTED, relief=tk.FLAT, bd=0, font=("Sans", 10, "bold"), padx=14, pady=8)
        self._stop_button.grid(row=0, column=1, sticky="e")
        self._paint_playback_status()

    def _set_mode(self, mode: str) -> None:
        if mode not in self._mode_buttons or mode == self._mode:
            return
        self._mode = mode
        self._paint_filters()
        self._render_stations() if mode == "favorites" else self._reload()

    def _toggle_internet_only(self) -> None:
        self._internet_only = not self._internet_only
        self._band_filter = "Internet-only" if self._internet_only else "All"
        label = self._filter_value_labels.get("band")
        if label is not None:
            label.configure(text=self._band_filter, fg=GREEN if self._internet_only else MUTED)
        self._paint_filters()
        self._render_stations()

    def _paint_filters(self) -> None:
        for mode, button in self._mode_buttons.items():
            active = mode == self._mode
            button.configure(fg=GREEN if active else TEXT, bg=CARD if active else PANEL)
        active_count = sum(value != "All" for value in (self._genre_filter, self._quality_filter, self._band_filter))
        label = "☰ FILTERS" if active_count == 0 else f"☰ FILTERS ({active_count})"
        self._filters_button.configure(text=label, fg=GREEN if active_count or self._filter_drawer_open else TEXT, bg=CARD if self._filter_drawer_open else PANEL)

    def _toggle_filter_drawer(self) -> None:
        if self._filter_drawer_open:
            self._close_filter_drawer()
            return
        if self._filter_drawer is None or not self._filter_drawer.winfo_exists():
            self._build_filter_drawer()
        self._filter_drawer.place(relx=1.0, rely=0.0, relheight=1.0, width=500, anchor="ne")
        self._filter_drawer.lift()
        self._filter_drawer_open = True
        self._paint_filters()

    def _close_filter_drawer(self) -> None:
        if self._filter_drawer is not None and self._filter_drawer.winfo_exists():
            self._filter_drawer.place_forget()
        self._filter_drawer_open = False
        self._paint_filters()

    def _build_filter_drawer(self) -> None:
        drawer = tk.Frame(self, bg=PANEL, highlightthickness=2, highlightbackground=BORDER)
        self._filter_drawer = drawer
        drawer.grid_columnconfigure(0, weight=1)
        header = tk.Frame(drawer, bg=CARD)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        tk.Label(header, text="STATION FILTERS", bg=CARD, fg=TEXT, font=("Sans", 13, "bold"), anchor="w", padx=12, pady=11).grid(row=0, column=0, sticky="ew")
        tk.Button(header, text="✕", command=self._close_filter_drawer, bg=CARD, fg=MUTED, activebackground=CARD_SELECTED, activeforeground=TEXT, relief=tk.FLAT, bd=0, font=("Sans", 13, "bold"), padx=12, pady=8).grid(row=0, column=1)
        body = tk.Frame(drawer, bg=PANEL, padx=12, pady=10)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1, uniform="filter-drawer")
        body.grid_columnconfigure(1, weight=1, uniform="filter-drawer")
        self._build_filter_group(body, row=0, column=0, title="MUSIC / CONTENT", key="genre", values=GENRE_FILTERS)
        self._build_filter_group(body, row=0, column=1, title="STREAM QUALITY", key="quality", values=QUALITY_FILTERS, helper="Low <96   Mid 96–191   High ≥192 kbps")
        self._build_filter_group(body, row=1, column=1, title="BAND / ORIGIN", key="band", values=BAND_FILTERS, helper="Internet-only lives here; broadcast band is best-effort metadata.")
        tk.Button(body, text="CLEAR FILTERS", command=self._clear_station_filters, bg=CARD, fg=TEXT, activebackground=CARD_SELECTED, activeforeground=GREEN, relief=tk.FLAT, bd=0, font=("Sans", 9, "bold"), pady=8).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 4))

    def _build_filter_group(self, parent: tk.Misc, *, row: int, column: int, title: str, key: str, values: tuple[str, ...], helper: str | None = None) -> None:
        group = tk.Frame(parent, bg=PANEL)
        group.grid(row=row, column=column, sticky="new", padx=(0, 6) if column == 0 else (6, 0), pady=(0, 10))
        group.grid_columnconfigure(0, weight=1)
        tk.Label(group, text=title, bg=PANEL, fg=BLUE, font=("Sans", 9, "bold"), anchor="w").grid(row=0, column=0, sticky="ew")
        current = {"genre": self._genre_filter, "quality": self._quality_filter, "band": self._band_filter}[key]
        value_label = tk.Label(group, text=current, bg=PANEL, fg=GREEN if current != "All" else MUTED, font=("Sans", 9, "bold"), anchor="e")
        value_label.grid(row=0, column=1, sticky="e")
        self._filter_value_labels[key] = value_label
        choices = tk.Frame(group, bg=PANEL)
        choices.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        columns = 2 if len(values) <= 6 else 3
        for choice_column in range(columns):
            choices.grid_columnconfigure(choice_column, weight=1)
        for index, value in enumerate(values):
            tk.Button(choices, text=value.upper(), command=lambda selected=value, filter_key=key: self._set_station_filter(filter_key, selected), bg=CARD, fg=TEXT, activebackground=CARD_SELECTED, activeforeground=GREEN, relief=tk.FLAT, bd=0, font=("Sans", 8, "bold"), padx=5, pady=6).grid(row=index // columns, column=index % columns, sticky="ew", padx=2, pady=2)
        if helper:
            tk.Label(group, text=helper, bg=PANEL, fg=MUTED, font=("Sans", 7), anchor="w", justify=tk.LEFT, wraplength=220).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    def _set_station_filter(self, key: str, value: str) -> None:
        if key == "genre":
            self._genre_filter = value
        elif key == "quality":
            self._quality_filter = value
        elif key == "band":
            self._band_filter = value
            self._internet_only = value == "Internet-only"
        else:
            raise ValueError(f"Unknown station filter: {key}")
        label = self._filter_value_labels.get(key)
        if label is not None:
            label.configure(text=value, fg=GREEN if value != "All" else MUTED)
        self._paint_filters()
        self._render_stations()

    def _clear_station_filters(self) -> None:
        self._genre_filter = "All"
        self._quality_filter = "All"
        self._band_filter = "All"
        self._internet_only = False
        for label in self._filter_value_labels.values():
            label.configure(text="All", fg=MUTED)
        self._paint_filters()
        self._render_stations()

    def _reload(self) -> None:
        if self._mode == "favorites":
            self._render_stations()
            return
        self._load_generation += 1
        generation = self._load_generation
        self._show_status("Loading local stations…" if self._mode == "local" else "Loading Michigan stations…")
        threading.Thread(target=self._load_worker, args=(generation, self._mode), name="orcui-streaming-radio-directory", daemon=True).start()

    def _load_worker(self, generation: int, mode: str) -> None:
        try:
            if mode == "local":
                stations = self._directory.stations_near(latitude=DETROIT_LATITUDE, longitude=DETROIT_LONGITUDE, radius_km=DETROIT_RADIUS_KM, state="Michigan", country_code="US", limit=50)
            else:
                stations = self._directory.stations_by_region(state="Michigan", country_code="US", limit=100)
        except Exception as error:
            self.after(0, lambda: self._finish_load(generation, (), error))
            return
        self.after(0, lambda: self._finish_load(generation, stations, None))

    def _finish_load(self, generation: int, stations: tuple[StreamingRadioStation, ...], error: Exception | None) -> None:
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
            if self._mode == "favorites":
                message = "No favorite stations match these filters."
            elif self._internet_only:
                message = "No internet-only stations match these filters."
            else:
                message = "No stations match these filters."
            self._show_status(message)
            return
        for index, station in enumerate(stations):
            self._build_station_card(station, row=index // CARD_COLUMNS, column=index % CARD_COLUMNS)

    def _visible_stations(self) -> tuple[StreamingRadioStation, ...]:
        stations = self._stations
        if self._mode == "favorites":
            stations = tuple(station for station in stations if station.station_id in self._favorites)
        if self._band_filter == "Internet-only":
            stations = tuple(station for station in stations if is_explicit_internet_only(station))
        else:
            stations = tuple(station for station in stations if not is_explicit_internet_only(station))
        if self._genre_filter != "All":
            stations = tuple(station for station in stations if station_genre_matches(station, self._genre_filter))
        if self._quality_filter != "All":
            stations = tuple(station for station in stations if station_quality(station) == self._quality_filter)
        if self._band_filter not in {"All", "Internet-only"}:
            stations = tuple(station for station in stations if station_band(station) == self._band_filter)
        return stations

    def _build_station_card(self, station: StreamingRadioStation, *, row: int, column: int) -> None:
        selected = self._selected_station is not None and station.station_id == self._selected_station.station_id
        current = self._controller.current_station
        playing = current is not None and current.station_id == station.station_id and self._controller.is_playing
        card_bg = "#142619" if playing else CARD_SELECTED if selected else CARD
        border = GREEN if playing else BLUE if selected else BORDER
        thickness = 3 if playing else 1
        card = tk.Frame(self._list, bg=card_bg, highlightthickness=thickness, highlightbackground=border)
        card.grid(row=row, column=column, sticky="nsew", padx=5, pady=5)
        card.grid_columnconfigure(1, weight=1)
        if playing:
            banner = tk.Label(card, text="●  NOW PLAYING", bg=GREEN, fg="#071006", font=("Sans", 9, "bold"), anchor="w", padx=8, pady=3)
            banner.grid(row=0, column=0, columnspan=3, sticky="ew")
            content_row = 1
        else:
            banner = None
            content_row = 0
        artwork = tk.Label(card, text="RADIO", bg="#081018", fg=MUTED, width=8, height=4, font=("Sans", 8, "bold"))
        artwork.grid(row=content_row, column=0, rowspan=3, padx=(8, 7), pady=8, sticky="w")
        self._apply_or_load_artwork(station, artwork)
        name = tk.Label(card, text=station.name, bg=card_bg, fg=GREEN if playing else TEXT, font=("Sans", 14 if playing else 11, "bold"), anchor="w", justify=tk.LEFT, wraplength=250)
        name.grid(row=content_row, column=1, columnspan=2, sticky="ew", padx=(0, 6), pady=(8, 1))
        details = _station_details(station)
        if is_explicit_internet_only(station):
            details = f"INTERNET ONLY • {details}"
        detail_label = tk.Label(card, text=details, bg=card_bg, fg=BLUE if is_explicit_internet_only(station) else MUTED, font=("Sans", 8), anchor="w", justify=tk.LEFT, wraplength=245)
        detail_label.grid(row=content_row + 1, column=1, columnspan=2, sticky="ew", padx=(0, 6), pady=(0, 4))
        favorite = station.station_id in self._favorites
        favorite_button = tk.Button(card, text="★" if favorite else "☆", command=lambda item=station: self._toggle_station_favorite(item), bg=card_bg, fg=GREEN if favorite else MUTED, activebackground=card_bg, activeforeground=GREEN, relief=tk.FLAT, bd=0, font=("Sans", 15), padx=5, pady=2)
        favorite_button.grid(row=content_row + 2, column=1, sticky="w", pady=(0, 6))
        play_button = tk.Button(card, text="■  STOP" if playing else "▶ PLAY", command=self._request_stop if playing else lambda item=station: self._request_play(item), state=tk.DISABLED if self._playback_busy else tk.NORMAL, bg=GREEN if playing else PANEL, fg="#071006" if playing else TEXT, activebackground="#9bdc45" if playing else CARD_SELECTED, activeforeground="#071006" if playing else GREEN, disabledforeground=MUTED, relief=tk.FLAT, bd=0, font=("Sans", 11 if playing else 9, "bold"), padx=14, pady=7 if playing else 5)
        play_button.grid(row=content_row + 2, column=2, sticky="e", padx=(4, 7), pady=(0, 6))
        clickable = [card, artwork, name, detail_label]
        if banner is not None:
            clickable.append(banner)
        for widget in clickable:
            widget.bind("<Button-1>", lambda _event, item=station: self._select_station(item))

    def _request_play(self, station: StreamingRadioStation) -> None:
        if self._playback_busy:
            return
        self._select_station(station)
        self._playback_busy = True
        self._selection_label.configure(text=f"Connecting to {station.name}…", fg=BLUE)
        self._render_stations()
        threading.Thread(target=self._playback_worker, args=(station,), name="orcui-streaming-radio-playback", daemon=True).start()

    def _request_stop(self) -> None:
        if self._playback_busy:
            return
        self._playback_busy = True
        self._selection_label.configure(text="Stopping stream…", fg=MUTED)
        self._render_stations()
        threading.Thread(target=self._playback_worker, args=(None,), name="orcui-streaming-radio-playback", daemon=True).start()

    def _playback_worker(self, station: StreamingRadioStation | None) -> None:
        try:
            self._controller.stop() if station is None else self._controller.play(station)
        except Exception as error:
            self.after(0, lambda: self._finish_playback(error))
            return
        self.after(0, lambda: self._finish_playback(None))

    def _finish_playback(self, error: Exception | None) -> None:
        if not self.winfo_exists():
            return
        self._playback_busy = False
        if error is not None:
            self._selection_label.configure(text=f"Playback failed: {type(error).__name__}: {error}", fg=DANGER)
        else:
            self._paint_playback_status()
        self._render_stations()

    def _paint_playback_status(self) -> None:
        current = self._controller.current_station
        if current is not None and self._controller.is_playing:
            self._selection_label.configure(text=f"● NOW PLAYING  •  {current.name}", fg=GREEN)
            self._stop_button.configure(state=tk.NORMAL, bg="#142619", fg=GREEN)
            return
        if self._selected_station is not None:
            self._selection_label.configure(text=self._selected_station.name, fg=TEXT)
        else:
            self._selection_label.configure(text="Select a station", fg=MUTED)
        self._stop_button.configure(state=tk.DISABLED, bg=PANEL, fg=TEXT)

    def _apply_or_load_artwork(self, station: StreamingRadioStation, label: tk.Label) -> None:
        image = self._artwork_images.get(station.station_id)
        if image is not None:
            label.configure(image=image, text="", width=ARTWORK_SIZE, height=ARTWORK_SIZE)
            return
        if not station.artwork_url or station.station_id in self._artwork_pending:
            return
        self._artwork_pending.add(station.station_id)
        future = self._artwork_executor.submit(_download_artwork, station.artwork_url)
        future.add_done_callback(lambda completed, item=station, target=label: self.after(0, lambda: self._finish_artwork(item, target, completed)))

    def _finish_artwork(self, station: StreamingRadioStation, label: tk.Label, future: object) -> None:
        self._artwork_pending.discard(station.station_id)
        if not self.winfo_exists():
            return
        try:
            pil_image = future.result()  # type: ignore[attr-defined]
        except Exception:
            return
        image = ImageTk.PhotoImage(pil_image)
        self._artwork_images[station.station_id] = image
        if label.winfo_exists():
            label.configure(image=image, text="", width=ARTWORK_SIZE, height=ARTWORK_SIZE)

    def _select_station(self, station: StreamingRadioStation) -> None:
        self._selected_station = station
        if not self._controller.is_playing:
            self._selection_label.configure(text=station.name, fg=TEXT)
        self._render_stations()
        if self._on_station_selected is not None:
            self._on_station_selected(station)

    def _toggle_station_favorite(self, station: StreamingRadioStation) -> None:
        self._selected_station = station
        if station.station_id in self._favorites:
            self._favorites.remove(station.station_id)
        else:
            self._favorites.add(station.station_id)
        self._paint_playback_status()
        self._render_stations()

    def _show_status(self, text: str, *, danger: bool = False) -> None:
        for child in self._list.winfo_children():
            child.destroy()
        tk.Label(self._list, text=text, bg=PANEL, fg=DANGER if danger else MUTED, font=("Sans", 11), pady=30).grid(row=0, column=0, columnspan=CARD_COLUMNS, sticky="ew")

    def _on_list_configure(self, _event: tk.Event[tk.Misc]) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event[tk.Misc]) -> None:
        self._canvas.itemconfigure(self._list_window, width=event.width)


def is_explicit_internet_only(station: StreamingRadioStation) -> bool:
    tags = {_normalize_tag(tag) for tag in station.tags}
    return bool(tags & {"internet", "internet only", "online only", "web radio", "webradio"})


def station_genre_matches(station: StreamingRadioStation, genre: str) -> bool:
    if genre == "All":
        return True
    accepted = _GENRE_TAGS.get(genre)
    if accepted is None:
        return False
    tags = {_normalize_tag(tag) for tag in station.tags}
    return bool(tags & {_normalize_tag(tag) for tag in accepted})


def station_quality(station: StreamingRadioStation) -> str:
    bitrate = station.bitrate_kbps
    if bitrate is None or bitrate <= 0:
        return "Unknown"
    if bitrate < 96:
        return "Low"
    if bitrate < 192:
        return "Mid"
    return "High"


def station_band(station: StreamingRadioStation) -> str:
    if is_explicit_internet_only(station):
        return "Internet-only"
    tags = {_normalize_tag(tag) for tag in station.tags}
    if tags & {"dab", "dab+", "digital audio broadcasting", "dabradio"}:
        return "DAB"
    if tags & {"fm", "fm radio", "fmradio"}:
        return "FM"
    if tags & {"am", "am radio", "amradio", "medium wave", "mw"}:
        return "AM"
    name = station.name.casefold()
    if re.search(r"\bfm\b", name):
        return "FM"
    if re.search(r"\bam\b", name):
        return "AM"
    for match in re.finditer(r"(?<!\d)(\d{2,3}\.\d)(?!\d)", name):
        frequency = float(match.group(1))
        if 87.5 <= frequency <= 108.0:
            return "FM"
    if re.search(r"\b(?:5[3-9]\d|[6-9]\d{2}|1[0-6]\d{2}|1700|1710)\s*(?:khz|am)\b", name):
        return "AM"
    return "Unknown"


def _normalize_tag(tag: str) -> str:
    return " ".join(tag.casefold().replace("_", " ").replace("-", " ").split())


def _download_artwork(url: str) -> Image.Image:
    request = Request(url, headers={"User-Agent": ARTWORK_USER_AGENT})
    with urlopen(request, timeout=ARTWORK_TIMEOUT_S) as response:
        payload = response.read(2 * 1024 * 1024 + 1)
    if len(payload) > 2 * 1024 * 1024:
        raise ValueError("station artwork exceeds 2 MiB")
    with Image.open(BytesIO(payload)) as image:
        converted = image.convert("RGBA")
        fitted = ImageOps.fit(converted, (ARTWORK_SIZE, ARTWORK_SIZE), method=Image.Resampling.LANCZOS)
        return fitted.copy()


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
