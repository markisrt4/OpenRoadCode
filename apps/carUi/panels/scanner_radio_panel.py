from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Callable

from apps.common.uiTheme import COLORS, MENU_TILE_STYLE


@dataclass(frozen=True)
class ScannerBandTileSpec:
    """Define the content of one scanner-band selection tile."""
    key: str
    icon: str
    label: str
    subtitle: str
    detail: str


class ScannerRadioPanel(tk.Frame):
    """Render the grid of selectable scanner bands."""
    def __init__(
        self,
        parent: tk.Widget,
        bands: list[ScannerBandTileSpec],
        on_band_pressed: Callable[[str], None],
        create_tile: Callable[[tk.Widget, str, str, str, str], tk.Frame],
        compact_ui: bool = False,
    ) -> None:
        super().__init__(parent, bg=COLORS["app_bg"])
        self._bands = tuple(bands)
        self._on_band_pressed = on_band_pressed
        self._create_tile = create_tile
        self._style = MENU_TILE_STYLE["compact" if compact_ui else "normal"]
        self._build_ui()

    def _build_ui(self) -> None:
        grid = tk.Frame(self, bg=COLORS["app_bg"])
        grid.pack(fill="both", expand=True)

        column_count = 4
        row_count = max(1, (len(self._bands) + column_count - 1) // column_count)

        for column in range(column_count):
            grid.columnconfigure(column, weight=1, uniform="scanner_col")
        for row in range(row_count):
            grid.rowconfigure(row, weight=1, uniform="scanner_row")

        for index, band in enumerate(self._bands):
            row = index // column_count
            column = index % column_count
            title = f"{band.icon}  {band.label}" if band.icon else band.label

            tile = self._create_tile(grid, band.key, title, band.subtitle, band.detail)
            tile.grid(
                row=row,
                column=column,
                sticky="nsew",
                padx=self._style["tile_padx"],
                pady=self._style["tile_pady"],
            )
            self._bind_click_recursive(
                tile,
                lambda key=band.key: self._on_band_pressed(key),
            )

    def _bind_click_recursive(self, widget: tk.Widget, callback: Callable[[], None]) -> None:
        widget.bind("<Button-1>", lambda event: callback())
        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback)
