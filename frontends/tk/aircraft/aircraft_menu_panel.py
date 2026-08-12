# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any


class AircraftMenuPanel(tk.Frame):
    """Aircraft feature menu containing ADS-B and Airband actions."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        on_adsb_pressed: Callable[[], None],
        on_airband_pressed: Callable[[], None],
        create_tile: Callable[
            [tk.Widget, str, str, str, str],
            tk.Frame,
        ],
        theme: dict[str, Any],
    ) -> None:
        self._on_adsb_pressed = on_adsb_pressed
        self._on_airband_pressed = on_airband_pressed
        self._create_tile = create_tile
        self._colors = theme["colors"]
        self._layout = theme["layout"]
        self._style = theme["profiles"]["default"]
        self._tiles = theme["tiles"]

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

        callbacks = {
            "adsb": self._on_adsb_pressed,
            "airband": self._on_airband_pressed,
        }

        for column, tile_spec in enumerate(self._tiles):
            tile = self._create_tile(
                grid,
                tile_spec["key"],
                tile_spec["title"],
                tile_spec["subtitle"],
                tile_spec["detail"],
            )
            tile.grid(
                row=self._layout["row"],
                column=column,
                sticky=self._layout["sticky"],
                padx=self._style["tile_padx"],
                pady=self._style["tile_pady"],
            )
            self._bind_click_recursive(
                tile,
                callbacks[tile_spec["action"]],
            )

    def _bind_click_recursive(
        self,
        widget: tk.Widget,
        callback: Callable[[], None],
    ) -> None:
        widget.bind("<Button-1>", lambda _event: callback())

        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback)
