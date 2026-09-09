# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Streaming-radio presentation with persistent favorite identifiers."""

from __future__ import annotations

import threading

from controllers.radio.streaming_radio_favorites import StreamingRadioFavorites
from controllers.radio.streaming_radio_filters import StationFilters
from controllers.radio.streaming_radio_types import StreamingRadioStation
from frontends.tk.radio.streaming_radio_panel import DANGER, StreamingRadioPanel


class PersistentStreamingRadioPanel(StreamingRadioPanel):
    """Persist favorite UUIDs and resolve current metadata on demand."""

    def __init__(self, *args, favorites: StreamingRadioFavorites, **kwargs) -> None:
        self._favorites_store = favorites
        super().__init__(*args, **kwargs)
        self._favorites = set(favorites.station_ids)

    def _visible_stations(self) -> tuple[StreamingRadioStation, ...]:
        """Apply the shared filter contract without changing directory ordering."""
        stations = self._stations
        if self._mode == "favorites":
            stations = tuple(
                station for station in stations
                if station.station_id in self._favorites
            )
        return StationFilters(
            genre=self._genre_filter,
            quality=self._quality_filter,
            band=self._band_filter,
        ).apply(stations)

    def _set_mode(self, mode: str) -> None:
        if mode not in self._mode_buttons or mode == self._mode:
            return
        self._mode = mode
        self._paint_filters()
        self._reload()

    def _reload(self) -> None:
        if self._mode != "favorites":
            super()._reload()
            return

        self._load_generation += 1
        generation = self._load_generation
        station_ids = self._favorites_store.ordered_station_ids
        if not station_ids:
            self._stations = ()
            self._render_stations()
            return

        self._show_status("Loading favorite stations…")
        threading.Thread(
            target=self._load_favorites_worker,
            args=(generation, station_ids),
            name="orcui-streaming-radio-favorites",
            daemon=True,
        ).start()

    def _load_favorites_worker(
        self,
        generation: int,
        station_ids: tuple[str, ...],
    ) -> None:
        try:
            stations = self._directory.stations_by_ids(station_ids)
        except Exception as error:
            self.after(
                0,
                lambda captured_error=error: self._finish_load(
                    generation,
                    (),
                    captured_error,
                ),
            )
            return
        self.after(0, lambda: self._finish_load(generation, stations, None))

    def _toggle_station_favorite(self, station: StreamingRadioStation) -> None:
        try:
            self._favorites_store.toggle(station.station_id)
        except (OSError, ValueError) as error:
            self._selection_label.configure(
                text=f"Unable to save favorite: {error}",
                fg=DANGER,
            )
            return

        self._favorites = set(self._favorites_store.station_ids)
        self._selected_station = station
        self._paint_playback_status()
        if self._mode == "favorites":
            self._reload()
        else:
            self._render_stations()
