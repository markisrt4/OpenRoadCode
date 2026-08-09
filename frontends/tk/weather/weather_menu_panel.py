from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any


class WeatherMenuPanel(tk.Frame):
    """Weather feature menu containing dashboard and NOAA radio actions."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        on_weather_dashboard_pressed: Callable[[], None],
        on_noaa_radio_pressed: Callable[[], None],
        create_tile: Callable[
            [tk.Widget, str, str, str, str],
            tk.Frame,
        ],
        theme: dict[str, Any],
    ) -> None:
        self._on_weather_dashboard_pressed = on_weather_dashboard_pressed
        self._on_noaa_radio_pressed = on_noaa_radio_pressed
        self._create_tile = create_tile
        self._theme = theme
        self._colors = theme["colors"]
        self._layout = theme["layout"]
        self._style = theme["profiles"]["default"]

        super().__init__(parent, bg=self._colors["background"])
        self._build_ui()

    def _build_ui(self) -> None:
        grid = tk.Frame(self, bg=self._colors["background"])
        grid.pack(
            fill=self._layout["fill_both"],
            expand=True,
        )

        for column in range(self._layout["columns"]):
            grid.columnconfigure(
                column,
                weight=self._layout["fill_weight"],
                uniform=self._layout["column_uniform"],
            )

        grid.rowconfigure(
            self._layout["row"],
            weight=self._layout["fill_weight"],
            uniform=self._layout["row_uniform"],
        )

        dashboard_tile = self._create_tile(
            grid,
            self._layout["dashboard_key"],
            self._layout["dashboard_title"],
            self._layout["dashboard_subtitle"],
            self._layout["dashboard_detail"],
        )
        dashboard_tile.grid(
            row=self._layout["row"],
            column=self._layout["dashboard_column"],
            sticky=self._layout["sticky"],
            padx=self._style["tile_padx"],
            pady=self._style["tile_pady"],
        )
        self._bind_click_recursive(
            dashboard_tile,
            self._on_weather_dashboard_pressed,
        )

        noaa_tile = self._create_tile(
            grid,
            self._layout["noaa_key"],
            self._layout["noaa_title"],
            self._layout["noaa_subtitle"],
            self._layout["noaa_detail"],
        )
        noaa_tile.grid(
            row=self._layout["row"],
            column=self._layout["noaa_column"],
            sticky=self._layout["sticky"],
            padx=self._style["tile_padx"],
            pady=self._style["tile_pady"],
        )
        self._bind_click_recursive(
            noaa_tile,
            self._on_noaa_radio_pressed,
        )

    def _bind_click_recursive(
        self,
        widget: tk.Widget,
        callback: Callable[[], None],
    ) -> None:
        widget.bind("<Button-1>", lambda _event: callback())

        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback)
