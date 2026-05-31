import tkinter as tk
from typing import Callable

from apps.carUi.volume_indicator import VolumeIndicator
from apps.common.uiTheme import COLORS, FONTS


class CarTopBar(tk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        compact_ui: bool,
        on_back: Callable[[], None],
        on_volume_down: Callable[[], None],
        on_volume_up: Callable[[], None],
        on_power: Callable[[], None],
        volume_level: int = 5,
        volume_steps: int = 8,
    ) -> None:
        height = 50 if compact_ui else 68
        super().__init__(parent, bg=COLORS["top_bar_bg"], height=height)

        self.compact_ui = compact_ui
        self.volume_steps = volume_steps

        self.title_var = tk.StringVar(value="CarSDR" if compact_ui else "Mark's CarSDR Control Panel")
        self.frequency_var = tk.StringVar(value="--")
        self.location_var = tk.StringVar(value="🌎 lat.--, lon.--")

        self.pack_propagate(False)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)

        self._build(
            on_back=on_back,
            on_volume_down=on_volume_down,
            on_volume_up=on_volume_up,
            on_power=on_power,
            volume_level=volume_level,
        )

    def _build(
        self,
        on_back: Callable[[], None],
        on_volume_down: Callable[[], None],
        on_volume_up: Callable[[], None],
        on_power: Callable[[], None],
        volume_level: int,
    ) -> None:
        small = self.compact_ui

        left_group = tk.Frame(self, bg=COLORS["top_bar_bg"])
        left_group.grid(row=0, column=0, sticky="w", padx=(8, 0), pady=6 if small else 8)

        center_group = tk.Frame(self, bg=COLORS["top_bar_bg"])
        center_group.grid(row=0, column=1, sticky="nsew", pady=6 if small else 8)

        right_group = tk.Frame(self, bg=COLORS["top_bar_bg"])
        right_group.grid(row=0, column=2, sticky="e", padx=(0, 10 if small else 16), pady=6 if small else 8)

        self.back_button = tk.Button(
            left_group,
            text="",
            font=(("Arial", 12, "bold") if small else FONTS["back"]),
            bg=COLORS["top_bar_bg"],
            fg=COLORS["top_bar_fg"],
            activebackground=COLORS["top_bar_active"],
            activeforeground=COLORS["top_bar_fg"],
            bd=1,
            padx=10 if small else 16,
            pady=4 if small else 6,
            cursor="hand2",
            command=on_back,
        )
        self.back_button.pack(side="left", padx=(0, 8 if small else 12))
        self.back_button.pack_forget()

        self.title_label = tk.Label(
            left_group,
            textvariable=self.title_var,
            font=(("Arial", 16, "bold") if small else FONTS["title"]),
            bg=COLORS["top_bar_bg"],
            fg=COLORS["top_bar_fg"],
        )
        self.title_label.pack(side="left")

        self.freq_label = tk.Label(
            center_group,
            textvariable=self.frequency_var,
            font=(("Arial", 13, "bold") if small else ("Arial", 18, "bold")),
            bg=COLORS["top_bar_bg"],
            fg=COLORS["top_bar_fg"],
            anchor="center",
        )
        self.freq_label.pack(expand=True)

        self.location_label = tk.Label(
            right_group,
            textvariable=self.location_var,
            font=(("Arial", 9) if small else FONTS["status"]),
            bg=COLORS["top_bar_bg"],
            fg=COLORS["top_bar_fg"],
            padx=6 if small else 10,
        )
        self.location_label.pack(side="left", padx=(0, 8 if small else 12))

        self.vol_down_button = tk.Button(
            right_group,
            text="−",
            font=FONTS["volume_button"],
            bg=COLORS["volume_button_bg"],
            fg=COLORS["volume_button_fg"],
            activebackground=COLORS["top_bar_active"],
            activeforeground=COLORS["volume_button_fg"],
            bd=0,
            width=3,
            height=1,
            command=on_volume_down,
            cursor="hand2",
        )
        self.vol_down_button.pack(side="left", padx=(0, 4))

        self.volume_indicator = VolumeIndicator(
            right_group,
            steps=self.volume_steps,
            initial_level=volume_level,
            bg=COLORS["top_bar_bg"],
            active=COLORS["volume_indicator_active"],
            inactive=COLORS["volume_indicator_inactive"],
        )
        self.volume_indicator.pack(side="left", padx=(4, 6))

        self.vol_up_button = tk.Button(
            right_group,
            text="+",
            font=FONTS["volume_button"],
            bg=COLORS["volume_button_bg"],
            fg=COLORS["volume_button_fg"],
            activebackground=COLORS["top_bar_active"],
            activeforeground=COLORS["volume_button_fg"],
            bd=0,
            width=3,
            height=1,
            command=on_volume_up,
            cursor="hand2",
        )
        self.vol_up_button.pack(side="left", padx=(0, 8))

        self.power_button = tk.Button(
            right_group,
            text="⏻",
            font=(("Arial", 14, "bold") if small else ("Arial", 18, "bold")),
            width=3 if small else 4,
            height=1,
            bg=COLORS["power_bg"],
            fg=COLORS["power_fg"],
            activebackground=COLORS["power_active"],
            activeforeground=COLORS["power_fg"],
            bd=0,
            command=on_power,
            cursor="hand2",
        )
        self.power_button.pack(side="right")

    def show_back_button(self, text: str = "‹") -> None:
        self.back_button.config(text=text)
        self.back_button.pack(side="left", padx=(0, 8 if self.compact_ui else 12))

    def hide_back_button(self) -> None:
        self.back_button.pack_forget()

    def set_title(self, title: str) -> None:
        compact_titles = {
            "NOAA Weather Radio": "NOAA WX",
            "FM Broadcast Radio": "FM Radio",
            "Airband AM Radio": "Airband",
            "Ham Radio": "HAM",
        }

        if self.compact_ui:
            title = compact_titles.get(title, title)

        self.title_var.set(title)

    def set_frequency_text(self, text: str) -> None:
        self.frequency_var.set(text)

    def set_location_text(self, text: str) -> None:
        self.location_var.set(text)

    def set_volume_level(self, level: int) -> None:
        self.volume_indicator.set_level(level)
