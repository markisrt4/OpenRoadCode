import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class AircraftTileSpec:
    key: str
    label: str
    subtitle: str
    detail: str


class AircraftPanel(tk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        on_adsb_pressed: Callable[[], None],
        on_airband_pressed: Callable[[], None],
        create_tile: Callable[[tk.Widget, str, str, str, str], tk.Frame],
    ) -> None:
        super().__init__(parent, bg="#111418")

        self.on_adsb_pressed = on_adsb_pressed
        self.on_airband_pressed = on_airband_pressed
        self.create_tile = create_tile

        self.tile_specs = [
            AircraftTileSpec(
                "adsb",
                "ADS-B",
                "Aircraft tracking",
                "Launch tar1090 web UI",
            ),
            AircraftTileSpec(
                "airband_am",
                "AIRBAND AM",
                "Aircraft chatter",
                "Launch SDR++ airband receiver",
            ),
        ]

        self._build_ui()

    def _build_ui(self) -> None:
        grid = tk.Frame(self, bg="#111418")
        grid.pack(fill="both", expand=True)

        grid.columnconfigure(0, weight=1, uniform="aircraft_col")
        grid.columnconfigure(1, weight=1, uniform="aircraft_col")
        grid.rowconfigure(0, weight=1, uniform="aircraft_row")

        for col, spec in enumerate(self.tile_specs):
            tile = self.create_tile(
                grid,
                spec.key,
                spec.label,
                spec.subtitle,
                spec.detail,
            )
            tile.grid(row=0, column=col, sticky="nsew", padx=10, pady=10)

            if spec.key == "adsb":
                self._bind_click_recursive(tile, self.on_adsb_pressed)
            elif spec.key == "airband_am":
                self._bind_click_recursive(tile, self.on_airband_pressed)

    def _bind_click_recursive(self, widget: tk.Widget, callback: Callable[[], None]) -> None:
        widget.bind("<Button-1>", lambda event: callback())
        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback)
