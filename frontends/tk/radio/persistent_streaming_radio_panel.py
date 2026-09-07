# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Streaming radio presentation with persistent favorites."""

from __future__ import annotations

from controllers.radio.streaming_radio_favorites import StreamingRadioFavorites
from controllers.radio.streaming_radio_types import StreamingRadioStation
from frontends.tk.radio.streaming_radio_panel import StreamingRadioPanel


class PersistentStreamingRadioPanel(StreamingRadioPanel):
    """Keep favorite records independently of the current directory results."""

    def __init__(self, *args, favorites: StreamingRadioFavorites, **kwargs) -> None:
        self._favorites_store = favorites
        super().__init__(*args, **kwargs)
        self._favorites = set(favorites.station_ids)

    def _visible_stations(self) -> tuple[StreamingRadioStation, ...]:
        if self._mode != "favorites":
            return super()._visible_stations()
        # Reuse the existing filtering policy, but supply the saved catalog.
        # The directory's current page must not determine which favorites exist.
        current = self._stations
        try:
            self._stations = self._favorites_store.stations
            return super()._visible_stations()
        finally:
            self._stations = current

    def _toggle_station_favorite(self, station: StreamingRadioStation) -> None:
        try:
            self._favorites_store.toggle(station)
        except (OSError, ValueError) as error:
            self._selection_label.configure(text=f"Unable to save favorite: {error}", fg="#f15a16")
            return
        self._favorites = set(self._favorites_store.station_ids)
        self._selected_station = station
        self._paint_playback_status()
        self._render_stations()
