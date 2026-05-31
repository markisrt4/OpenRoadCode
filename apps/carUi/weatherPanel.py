import tkinter as tk
from typing import Callable

from apps.common.uiTheme import COLORS

class WeatherPanel(tk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        on_weather_dashboard_pressed: Callable[[], None],
        on_noaa_radio_pressed: Callable[[], None],
        create_tile: Callable[[tk.Widget, str, str, str, str], tk.Frame],
    ) -> None:
        super().__init__(parent, bg=COLORS["app_bg"])

        self.on_weather_dashboard_pressed = on_weather_dashboard_pressed
        self.on_noaa_radio_pressed = on_noaa_radio_pressed
        self.create_tile = create_tile

        self._build_ui()

    def _build_ui(self) -> None:
        grid = tk.Frame(self, bg=COLORS["app_bg"])
        grid.pack(fill="both", expand=True)

        grid.columnconfigure(0, weight=1, uniform="weather_col")
        grid.columnconfigure(1, weight=1, uniform="weather_col")
        grid.rowconfigure(0, weight=1, uniform="weather_row")

        dashboard_tile = self.create_tile(
            grid,
            "weather_dashboard",
            "WEATHER DASHBOARD",
            "Forecast display",
            "Toggle Streamlit kiosk",
        )
        dashboard_tile.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self._bind_click_recursive(dashboard_tile, self.on_weather_dashboard_pressed)

        noaa_tile = self.create_tile(
            grid,
            "noaa_weather_radio",
            "NOAA WEATHER RADIO",
            "Weather band SDR",
            "Toggle SDR++ at NOAA preset",
        )
        noaa_tile.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self._bind_click_recursive(noaa_tile, self.on_noaa_radio_pressed)

    def _bind_click_recursive(self, widget: tk.Widget, callback: Callable[[], None]) -> None:
        widget.bind("<Button-1>", lambda event: callback())
        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback)
