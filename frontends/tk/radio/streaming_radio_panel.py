# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Touch-oriented streaming-radio browser for the ORC radio screen."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from io import BytesIO
from functools import partial

from PIL import Image, ImageOps, ImageTk

from ui.radio.streaming_radio_types import StreamingRadioStation
from ui.radio.streaming_radio_session_if import (
    StreamingRadioSessionIf,
    StreamingRadioRequestHandlerIf,
)
from ui.radio.streaming_radio_state import (
    StreamingRadioBrowserState,
    StreamingRadioBrowseMode,
    StreamingRadioPlaybackState,
)
from ui.radio.station_filters import (
    StationFilters,
)
from ui.ui_widget import UiWidget

from .streaming_radio_layout import (
    BG,
    PANEL,
    CARD,
    CARD_SELECTED,
    BORDER,
    TEXT,
    MUTED,
    GREEN,
    BLUE,
    DANGER,
    build_streaming_header,
    build_filter_drawer,
    build_filter_group,
    build_station_card,
)

ARTWORK_SIZE = 64
CARD_COLUMNS = 2

BackHandler = Callable[[], None]
StationHandler = Callable[[StreamingRadioStation], None]


class StreamingRadioPanel(tk.Frame, UiWidget):
    """Browse and play local/regional streaming radio stations."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        session: StreamingRadioSessionIf,
        on_back: BackHandler,
        on_station_selected: StationHandler | None = None,
    ) -> None:
        super().__init__(parent, bg=BG)
        self._session = session
        self._request_handler: StreamingRadioRequestHandlerIf | None = None
        self._playback = StreamingRadioPlaybackState()
        self._active = True
        self._destroyed = False
        self._on_back = on_back
        self._on_station_selected = on_station_selected
        self._mode = "local"
        self._internet_only = False
        self._favorites: set[str] = set()
        self._stations: tuple[StreamingRadioStation, ...] = ()
        self._selected_station: StreamingRadioStation | None = None
        self._playback_busy = False
        self._genre_filter = "All"
        self._quality_filter = "All"
        self._band_filter = "All"
        self._filter_drawer_open = False
        self._filter_drawer: tk.Frame | None = None
        self._filter_value_labels: dict[str, tk.Label] = {}
        self._artwork_images: dict[str, ImageTk.PhotoImage] = {}
        self._artwork_urls: dict[str, str | None] = {}
        self._artwork_labels: dict[str, tk.Label] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_header()
        self._build_filters()
        self._build_station_list()
        self._build_footer()
        self._session.activate(self)

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
        if self._destroyed:
            return
        self._destroyed = True
        try:
            self._session.close()
        finally:
            super().destroy()

    def activate(self) -> None:
        """Resume controller delivery when this browser becomes visible."""
        if not self._destroyed and not self._active:
            self._active = True
            self._session.activate(self)

    def deactivate(self) -> None:
        """Retire controller delivery while preserving application-owned audio."""
        self._active = False
        self._session.deactivate()

    def set_streaming_request_handler(self, handler: StreamingRadioRequestHandlerIf | None) -> None:
        self._request_handler = handler

    def set_streaming_state(self, state: StreamingRadioBrowserState) -> None:
        """Render a controller snapshot without consulting any backend."""
        self._mode = state.mode.value
        for station in state.stations:
            if self._artwork_urls.get(station.station_id) != station.artwork_url:
                self._artwork_images.pop(station.station_id, None)
            self._artwork_urls[station.station_id] = station.artwork_url
        self._stations = state.stations
        self._favorites = set(state.favorite_station_ids)
        self._playback = state.playback
        self._playback_busy = state.playback_busy
        self._paint_filters()
        if state.loading:
            messages = {
                "local": "Loading local stations…",
                "regional": "Loading Michigan stations…",
                "favorites": "Loading favorite stations…",
            }
            self._show_status(messages[self._mode])
        elif state.error and not state.stations:
            self._show_status(state.message, danger=True)
        else:
            self._render_stations()
        self._paint_playback_status()
        if state.message:
            self._selection_label.configure(text=state.message, fg=DANGER if state.error else BLUE)

    def _build_header(self) -> None:
        build_streaming_header(self)

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
                command=partial(self._set_mode, mode),
                bg=PANEL,
                fg=TEXT,
                activebackground=CARD_SELECTED,
                activeforeground=GREEN,
                relief=tk.FLAT,
                bd=0,
                font=("Sans", 14, "bold"),
                padx=10,
                pady=8,
                highlightthickness=0,
            )
            button.grid(row=0, column=column, sticky="ew")
            self._mode_buttons[mode] = button
        self._filters_button = tk.Button(
            filters,
            text="☰ FILTERS",
            command=self._toggle_filter_drawer,
            bg=PANEL,
            fg=TEXT,
            activebackground=CARD_SELECTED,
            activeforeground=GREEN,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 15, "bold"),
            padx=8,
            pady=8,
            highlightthickness=0,
        )
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
        self._selection_label = tk.Label(
            footer,
            text="Select a station",
            bg=PANEL,
            fg=MUTED,
            font=("Sans", 14, "bold"),
            anchor="w",
            padx=12,
            pady=8,
        )
        self._selection_label.grid(row=0, column=0, sticky="ew")
        self._stop_button = tk.Button(
            footer,
            text="■ STOP",
            command=self._request_stop,
            state=tk.NORMAL if self._playback.is_playing else tk.DISABLED,
            bg=PANEL,
            fg=TEXT,
            activebackground=CARD_SELECTED,
            activeforeground=DANGER,
            disabledforeground=MUTED,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 14, "bold"),
            padx=14,
            pady=8,
            highlightthickness=0,
        )
        self._stop_button.grid(row=0, column=1, sticky="e")
        self._paint_playback_status()

    def _set_mode(self, mode: str) -> None:
        if mode not in self._mode_buttons or mode == self._mode:
            return
        self._mode = mode
        self._paint_filters()
        self._reload()

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
        active_count = sum(
            value != "All"
            for value in (self._genre_filter, self._quality_filter, self._band_filter)
        )
        label = "☰ FILTERS" if active_count == 0 else f"☰ FILTERS ({active_count})"
        self._filters_button.configure(
            text=label,
            fg=GREEN if active_count or self._filter_drawer_open else TEXT,
            bg=CARD if self._filter_drawer_open else PANEL,
        )

    def _toggle_filter_drawer(self) -> None:
        if self._filter_drawer_open:
            self._close_filter_drawer()
            return
        if self._filter_drawer is None or not self._filter_drawer.winfo_exists():
            self._build_filter_drawer()
        drawer = self._filter_drawer
        if drawer is None:
            return
        drawer.place(relx=1.0, rely=0.0, relheight=1.0, width=500, anchor="ne")
        drawer.lift()
        self._filter_drawer_open = True
        self._paint_filters()

    def _close_filter_drawer(self) -> None:
        if self._filter_drawer is not None and self._filter_drawer.winfo_exists():
            self._filter_drawer.place_forget()
        self._filter_drawer_open = False
        self._paint_filters()

    def _build_filter_drawer(self) -> None:
        build_filter_drawer(self)

    def _build_filter_group(
        self,
        parent: tk.Misc,
        *,
        row: int,
        column: int,
        title: str,
        key: str,
        values: tuple[str, ...],
        helper: str | None = None,
    ) -> None:
        build_filter_group(
            self, parent, row=row, column=column, title=title, key=key, values=values, helper=helper
        )

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
        handler = self._request_handler
        if handler is not None:
            handler.request_mode(StreamingRadioBrowseMode(self._mode))

    def _render_stations(self) -> None:
        self._artwork_labels.clear()
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
            self._build_station_card(
                station, row=index // CARD_COLUMNS, column=index % CARD_COLUMNS
            )

    def _visible_stations(self) -> tuple[StreamingRadioStation, ...]:
        stations = self._stations
        if self._mode == "favorites":
            stations = tuple(s for s in stations if s.station_id in self._favorites)
        return StationFilters(
            genre=self._genre_filter,
            quality=self._quality_filter,
            band=self._band_filter,
        ).apply(stations)

    def _build_station_card(self, station: StreamingRadioStation, *, row: int, column: int) -> None:
        build_station_card(self, station, row=row, column=column)

    def _request_play(self, station: StreamingRadioStation) -> None:
        self._select_station(station)
        handler = self._request_handler
        if handler is not None:
            handler.request_play(station.station_id)

    def _request_stop(self) -> None:
        handler = self._request_handler
        if handler is not None:
            handler.request_stop()

    def _paint_playback_status(self) -> None:
        current = self._playback.station
        if current is not None and self._playback.is_playing:
            self._selection_label.configure(text=f"● NOW PLAYING  •  {current.name}", fg=GREEN)
            self._stop_button.configure(state=tk.NORMAL, bg="#142619", fg=GREEN)
            return
        if self._selected_station is not None:
            self._selection_label.configure(text=self._selected_station.name, fg=TEXT)
        else:
            self._selection_label.configure(text="Select a station", fg=MUTED)
        self._stop_button.configure(state=tk.DISABLED, bg=PANEL, fg=TEXT)

    def _apply_or_load_artwork(self, station: StreamingRadioStation, label: tk.Label) -> None:
        self._artwork_labels[station.station_id] = label
        image = self._artwork_images.get(station.station_id)
        if image is not None:
            label.configure(image=image, text="", width=ARTWORK_SIZE, height=ARTWORK_SIZE)
            return
        handler = self._request_handler
        if handler is not None and station.artwork_url:
            handler.request_artwork(station.station_id)

    def set_station_artwork(self, station_id: str, payload: bytes) -> None:
        """Decode display artwork and create toolkit objects on the frontend thread."""
        if self._destroyed or not self._active:
            return
        try:
            with Image.open(BytesIO(payload)) as source:
                fitted = ImageOps.fit(
                    source.convert("RGBA"),
                    (ARTWORK_SIZE, ARTWORK_SIZE),
                    method=Image.Resampling.LANCZOS,
                )
                image = ImageTk.PhotoImage(fitted)
        except (OSError, ValueError, Image.DecompressionBombError, tk.TclError):
            return
        self._artwork_images[station_id] = image
        label = self._artwork_labels.get(station_id)
        if label is not None and label.winfo_exists():
            label.configure(image=image, text="", width=ARTWORK_SIZE, height=ARTWORK_SIZE)

    def _select_station(self, station: StreamingRadioStation) -> None:
        self._selected_station = station
        if not self._playback.is_playing:
            self._selection_label.configure(text=station.name, fg=TEXT)
        self._render_stations()
        if self._on_station_selected is not None:
            self._on_station_selected(station)

    def _toggle_station_favorite(self, station: StreamingRadioStation) -> None:
        self._selected_station = station
        handler = self._request_handler
        if handler is not None:
            handler.request_toggle_favorite(station.station_id)

    def _show_status(self, text: str, *, danger: bool = False) -> None:
        self._artwork_labels.clear()
        for child in self._list.winfo_children():
            child.destroy()
        tk.Label(
            self._list,
            text=text,
            bg=PANEL,
            fg=DANGER if danger else MUTED,
            font=("Sans", 14),
            pady=30,
        ).grid(row=0, column=0, columnspan=CARD_COLUMNS, sticky="ew")

    def _on_list_configure(self, _event: tk.Event[tk.Misc]) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event[tk.Misc]) -> None:
        self._canvas.itemconfigure(self._list_window, width=event.width)
