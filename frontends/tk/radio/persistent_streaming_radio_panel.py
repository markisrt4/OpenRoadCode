# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Streaming-radio presentation with persistent favorite identifiers."""

from __future__ import annotations

import threading
import tkinter as tk

from controllers.radio.streaming_radio_favorites import StreamingRadioFavorites
from controllers.radio.streaming_radio_filters import StationFilters
from controllers.radio.streaming_radio_types import StreamingRadioStation
from frontends.tk.radio.streaming_radio_panel import (
    BG,
    BLUE,
    BORDER,
    CARD,
    CARD_SELECTED,
    DANGER,
    GREEN,
    MUTED,
    PANEL,
    TEXT,
    StreamingRadioPanel,
)
from ui.theme import ThemeBundle


class PersistentStreamingRadioPanel(StreamingRadioPanel):
    """Persist favorite UUIDs and resolve current metadata on demand."""

    def __init__(
        self,
        *args,
        favorites: StreamingRadioFavorites,
        theme: ThemeBundle,
        **kwargs,
    ) -> None:
        self._favorites_store = favorites
        self._theme_bundle = theme
        super().__init__(*args, **kwargs)
        self._favorites = set(favorites.station_ids)
        self._apply_theme()

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        """Apply the current ORC semantic theme to the legacy streaming widgets."""
        previous = self._theme_bundle
        self._theme_bundle = theme
        self._render_stations()
        self._apply_theme(previous)

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
                fg=self._theme_bundle.ui.accent_danger,
            )
            return

        self._favorites = set(self._favorites_store.station_ids)
        self._selected_station = station
        self._paint_playback_status()
        if self._mode == "favorites":
            self._reload()
        else:
            self._render_stations()

    def _render_stations(self) -> None:
        super()._render_stations()
        self._apply_theme()

    def _paint_filters(self) -> None:
        super()._paint_filters()
        self._apply_theme()

    def _paint_playback_status(self) -> None:
        super()._paint_playback_status()
        self._apply_theme()

    def _build_filter_drawer(self) -> None:
        super()._build_filter_drawer()
        self._apply_theme()

    def _show_status(self, text: str, *, danger: bool = False) -> None:
        super()._show_status(text, danger=danger)
        self._apply_theme()

    def _apply_theme(self, previous: ThemeBundle | None = None) -> None:
        if not hasattr(self, "_theme_bundle"):
            return
        ui = self._theme_bundle.ui
        colors = {
            BG: ui.background,
            PANEL: ui.surface,
            CARD: ui.surface_alt,
            CARD_SELECTED: ui.control_active,
            BORDER: ui.border,
            TEXT: ui.text,
            MUTED: ui.text_muted,
            GREEN: ui.accent_success,
            BLUE: ui.accent_primary,
            DANGER: ui.accent_danger,
            "#142619": ui.surface_alt,
            "#081018": ui.control_background,
            "#071006": ui.control_text,
            "#9bdc45": ui.control_active,
            "#ffffff": ui.text,
        }
        if previous is not None:
            old = previous.ui
            colors.update(
                {
                    old.background: ui.background,
                    old.surface: ui.surface,
                    old.surface_alt: ui.surface_alt,
                    old.border: ui.border,
                    old.text: ui.text,
                    old.text_muted: ui.text_muted,
                    old.accent_primary: ui.accent_primary,
                    old.accent_success: ui.accent_success,
                    old.accent_danger: ui.accent_danger,
                    old.control_background: ui.control_background,
                    old.control_active: ui.control_active,
                    old.control_text: ui.control_text,
                }
            )
        self._recolor_widget_tree(self, colors)

    @classmethod
    def _recolor_widget_tree(cls, widget: tk.Misc, colors: dict[str, str]) -> None:
        for option in (
            "background",
            "foreground",
            "activebackground",
            "activeforeground",
            "disabledforeground",
            "highlightbackground",
        ):
            try:
                current = str(widget.cget(option)).lower()
            except tk.TclError:
                continue
            replacement = colors.get(current)
            if replacement is not None and replacement.lower() != current:
                try:
                    widget.configure(**{option: replacement})
                except tk.TclError:
                    pass
        for child in widget.winfo_children():
            cls._recolor_widget_tree(child, colors)
