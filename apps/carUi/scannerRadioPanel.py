import tkinter as tk
from dataclasses import dataclass
from typing import Callable

from apps.common.uiTheme import COLORS, FONTS, FONT_FAMILY


@dataclass(frozen=True)
class ScannerBandTileSpec:
    key: str
    icon: str
    label: str
    subtitle: str
    detail: str


class ScannerRadioPanel(tk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        bands: list[ScannerBandTileSpec],
        on_band_pressed: Callable[[str], None],
        compact_ui: bool = False,
    ) -> None:
        super().__init__(parent, bg=COLORS["app_bg"])

        self.bands = bands
        self.on_band_pressed = on_band_pressed
        self.compact_ui = compact_ui

        self._build_ui()

    def _build_ui(self) -> None:
        grid = tk.Frame(self, bg=COLORS["app_bg"])
        grid.pack(fill="both", expand=True)

        for col in range(4):
            grid.columnconfigure(col, weight=1, uniform="scanner_col")
        for row in range(2):
            grid.rowconfigure(row, weight=1, uniform="scanner_row")

        for index, band in enumerate(self.bands):
            row = index // 4
            col = index % 4

            tile = self._create_scanner_tile(grid, band)
            tile.grid(
                row=row,
                column=col,
                sticky="nsew",
                padx=5 if self.compact_ui else 8,
                pady=5 if self.compact_ui else 8,
            )

            self._bind_click_recursive(
                tile,
                lambda key=band.key: self.on_band_pressed(key),
            )

    def _create_scanner_tile(
        self,
        parent: tk.Widget,
        band: ScannerBandTileSpec,
    ) -> tk.Frame:
        tile = tk.Frame(
            parent,
            bg=COLORS["tile_bg"],
            highlightthickness=2,
            highlightbackground=COLORS["tile_border"],
            highlightcolor=COLORS["tile_accent"],
            bd=0,
            cursor="hand2",
        )

        accent = tk.Frame(tile, bg=COLORS["tile_accent"], height=4)
        accent.pack(fill="x", side="top")

        body = tk.Frame(tile, bg=COLORS["tile_bg"])
        body.pack(
            fill="both",
            expand=True,
            padx=8 if self.compact_ui else 14,
            pady=7 if self.compact_ui else 12,
        )

        icon_label = tk.Label(
            body,
            text=band.icon,
            font=self._icon_font(),
            bg=COLORS["tile_bg"],
            fg=COLORS["tile_accent"],
            anchor="center",
        )
        icon_label.pack(anchor="w")

        title = tk.Label(
            body,
            text=band.label,
            font=self._title_font(),
            bg=COLORS["tile_bg"],
            fg=COLORS["tile_title"],
            anchor="w",
            justify="left",
            wraplength=150 if self.compact_ui else 220,
        )
        title.pack(fill="x", anchor="w", pady=(3, 0))

        subtitle = tk.Label(
            body,
            text=band.subtitle,
            font=self._subtitle_font(),
            bg=COLORS["tile_bg"],
            fg=COLORS["tile_subtitle"],
            anchor="w",
            justify="left",
            wraplength=150 if self.compact_ui else 220,
        )
        subtitle.pack(fill="x", anchor="w", pady=(4, 0))

        detail = tk.Label(
            body,
            text=band.detail,
            font=self._detail_font(),
            bg=COLORS["tile_bg"],
            fg=COLORS["tile_detail"],
            anchor="w",
            justify="left",
            wraplength=150 if self.compact_ui else 220,
        )
        detail.pack(fill="x", anchor="w", pady=(2, 0))

        return tile

    def _bind_click_recursive(
        self,
        widget: tk.Widget,
        callback: Callable[[], None],
    ) -> None:
        widget.bind("<Button-1>", lambda event: callback())

        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback)

    def _icon_font(self):
        return (FONT_FAMILY, 15 if self.compact_ui else 20, "bold")

    def _title_font(self):
        return (FONT_FAMILY, 13 if self.compact_ui else 18, "bold")

    def _subtitle_font(self):
        return (FONT_FAMILY, 9 if self.compact_ui else 12)

    def _detail_font(self):
        return (FONT_FAMILY, 8 if self.compact_ui else 10)
