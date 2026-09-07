# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Touch-oriented streaming-radio browser for the ORC radio screen."""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from urllib.request import Request, urlopen

from PIL import Image, ImageOps, ImageTk

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
ARTWORK_SIZE = 72
ARTWORK_TIMEOUT_S = 5.0
ARTWORK_USER_AGENT = "OpenRoadCode/streaming-radio"


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
        self._internet_only = False
        self._favorites: set[str] = set()
        self._stations: tuple[StreamingRadioStation, ...] = ()
        self._selected_station: StreamingRadioStation | None = None
        self._load_generation = 0
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
        """Compatibility property; True now means exclusive internet-only mode."""
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
                activebackground=CARD_SELECTED,
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
            text="INTERNET ONLY: OFF",
            command=self._toggle_internet_only,
            bg=PANEL,
            fg=MUTED,
            activebackground=CARD_SELECTED,
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
            activebackground=CARD_SELECTED,
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
        self._internet_only = not self._internet_only
        self._paint_filters()
        self._render_stations()

    def _paint_filters(self) -> None:
        for mode, button in self._mode_buttons.items():
            active = mode == self._mode
            button.configure(fg=GREEN if active else TEXT, bg=CARD if active else PANEL)
        state = "ON" if self._internet_only else "OFF"
        self._internet_button.configure(
            text=f"INTERNET ONLY: {state}",
            fg=BLUE if self._internet_only else MUTED,
            bg=CARD if self._internet_only else PANEL,
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
            if self._mode == "favorites":
                message = "No favorite stations in this view."
            elif self._internet_only:
                message = "No stations explicitly identified as internet-only."
            else:
                message = "No stations found."
            self._show_status(message)
            return

        for station in stations:
            self._build_station_card(station)

    def _visible_stations(self) -> tuple[StreamingRadioStation, ...]:
        stations = self._stations
        if self._mode == "favorites":
            stations = tuple(station for station in stations if station.station_id in self._favorites)
        if self._internet_only:
            return tuple(station for station in stations if is_explicit_internet_only(station))
        return tuple(station for station in stations if not is_explicit_internet_only(station))

    def _build_station_card(self, station: StreamingRadioStation) -> None:
        selected = self._selected_station is not None and station.station_id == self._selected_station.station_id
        card_bg = CARD_SELECTED if selected else CARD
        card = tk.Frame(self._list, bg=card_bg, highlightthickness=1, highlightbackground=BLUE if selected else BORDER)
        card.pack(fill=tk.X, padx=6, pady=5)
        card.grid_columnconfigure(1, weight=1)

        artwork = tk.Label(
            card,
            text="RADIO",
            bg="#081018",
            fg=MUTED,
            width=9,
            height=4,
            font=("Sans", 9, "bold"),
        )
        artwork.grid(row=0, column=0, rowspan=2, padx=10, pady=9, sticky="w")
        self._apply_or_load_artwork(station, artwork)

        tk.Label(card, text=station.name, bg=card_bg, fg=TEXT, font=("Sans", 13, "bold"), anchor="w").grid(
            row=0, column=1, sticky="sew", padx=(0, 8), pady=(10, 2)
        )
        details = _station_details(station)
        if is_explicit_internet_only(station):
            details = f"INTERNET ONLY  •  {details}"
        tk.Label(card, text=details, bg=card_bg, fg=BLUE if is_explicit_internet_only(station) else MUTED, font=("Sans", 9), anchor="w").grid(
            row=1, column=1, sticky="new", padx=(0, 8), pady=(0, 10)
        )

        favorite = station.station_id in self._favorites
        favorite_label = tk.Label(
            card,
            text="★" if favorite else "☆",
            bg=card_bg,
            fg=GREEN if favorite else MUTED,
            font=("Sans", 18),
            padx=12,
        )
        favorite_label.grid(row=0, column=2, rowspan=2, sticky="e")

        for widget in (card, artwork, *card.winfo_children()):
            if widget is favorite_label:
                continue
            widget.bind("<Button-1>", lambda _event, item=station: self._select_station(item))
        favorite_label.bind("<Button-1>", lambda _event, item=station: self._toggle_station_favorite(item))

    def _apply_or_load_artwork(self, station: StreamingRadioStation, label: tk.Label) -> None:
        image = self._artwork_images.get(station.station_id)
        if image is not None:
            label.configure(image=image, text="", width=ARTWORK_SIZE, height=ARTWORK_SIZE)
            return
        if not station.artwork_url or station.station_id in self._artwork_pending:
            return

        self._artwork_pending.add(station.station_id)
        future = self._artwork_executor.submit(_download_artwork, station.artwork_url)
        future.add_done_callback(
            lambda completed, item=station, target=label: self.after(
                0, lambda: self._finish_artwork(item, target, completed)
            )
        )

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
        self._selection_label.configure(text=station.name, fg=TEXT)
        self._favorite_button.configure(state=tk.NORMAL)
        self._paint_favorite_button()
        self._render_stations()
        if self._on_station_selected is not None:
            self._on_station_selected(station)

    def _toggle_station_favorite(self, station: StreamingRadioStation) -> None:
        self._selected_station = station
        self._toggle_favorite()

    def _toggle_favorite(self) -> None:
        station = self._selected_station
        if station is None:
            return
        if station.station_id in self._favorites:
            self._favorites.remove(station.station_id)
        else:
            self._favorites.add(station.station_id)
        self._selection_label.configure(text=station.name, fg=TEXT)
        self._favorite_button.configure(state=tk.NORMAL)
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


def _download_artwork(url: str) -> Image.Image:
    request = Request(url, headers={"User-Agent": ARTWORK_USER_AGENT})
    with urlopen(request, timeout=ARTWORK_TIMEOUT_S) as response:
        payload = response.read(2 * 1024 * 1024 + 1)
    if len(payload) > 2 * 1024 * 1024:
        raise ValueError("station artwork exceeds 2 MiB")
    with Image.open(BytesIO(payload)) as image:
        converted = image.convert("RGB")
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
