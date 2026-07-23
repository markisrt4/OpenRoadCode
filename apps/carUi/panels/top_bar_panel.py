from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from typing import Any

from apps.carUi.system.volume_indicator import VolumeIndicator, VolumeIndicatorStyle


LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "openroadcode.png"


class TopBarPanel(tk.Frame):
    """Render shared navigation, title, frequency, location, and volume UI."""
    def __init__(
        self,
        parent: tk.Widget,
        *,
        compact_ui: bool,
        theme: dict[str, Any],
        on_back: Callable[[], None],
        on_volume_down: Callable[[], None],
        on_volume_up: Callable[[], None],
        on_settings: Callable[[], None],
        on_power: Callable[[], None],
        volume_level: int,
        volume_steps: int,
        volume_muted: bool,
    ) -> None:
        self._theme = theme
        self._colors = theme["colors"]
        self._layout = theme["layout"]
        self._style = theme["profiles"]["compact" if compact_ui else "normal"]
        self._compact_ui = compact_ui

        super().__init__(
            parent,
            bg=self._colors["background"],
            height=self._style["height"],
        )

        self.title_var = tk.StringVar(value=self._style["default_title"])
        self.frequency_var = tk.StringVar(value=self._layout["empty_frequency"])
        self.location_var = tk.StringVar(value=self._layout["empty_location"])

        self.pack_propagate(False)

        for column in range(self._layout["column_count"]):
            self.columnconfigure(column, weight=self._layout["column_weight"])

        self._build(
            on_back=on_back,
            on_volume_down=on_volume_down,
            on_volume_up=on_volume_up,
            on_settings=on_settings,
            on_power=on_power,
            volume_level=volume_level,
            volume_steps=volume_steps,
            volume_muted=volume_muted,
        )

    def show_back_button(self, text: str | None = None) -> None:
        self.back_button.config(text=text or self._layout["back_button_text"])
        self.back_button.pack(
            side=self._layout["left_side"],
            padx=(self._layout["zero"], self._style["back_button_gap"]),
        )

    def hide_back_button(self) -> None:
        self.back_button.pack_forget()

    def set_back_command(self, command: Callable[[], None]) -> None:
        self.back_button.config(command=command)

    def set_title(self, title: str) -> None:
        if self._compact_ui:
            title = self._theme["compact_titles"].get(title, title)
        self.title_var.set(title)

    def set_frequency_text(self, text: str) -> None:
        self.frequency_var.set(text)

    def set_location_text(self, text: str) -> None:
        self.location_var.set(text)

    def set_volume_level(self, level: int) -> None:
        self.volume_indicator.set_level(level)

    def set_volume_muted(self, muted: bool) -> None:
        self.volume_indicator.set_muted(muted)

    def _build(
        self,
        *,
        on_back: Callable[[], None],
        on_volume_down: Callable[[], None],
        on_volume_up: Callable[[], None],
        on_settings: Callable[[], None],
        on_power: Callable[[], None],
        volume_level: int,
        volume_steps: int,
        volume_muted: bool,
    ) -> None:
        left_group = tk.Frame(self, bg=self._colors["background"])
        left_group.grid(
            row=self._layout["row"],
            column=self._layout["left_column"],
            sticky=self._layout["left_sticky"],
            padx=(self._style["left_padx"], self._layout["zero"]),
            pady=self._style["group_pady"],
        )

        center_group = tk.Frame(self, bg=self._colors["background"])
        center_group.grid(
            row=self._layout["row"],
            column=self._layout["center_column"],
            sticky=self._layout["fill_sticky"],
            pady=self._style["group_pady"],
        )

        right_group = tk.Frame(self, bg=self._colors["background"])
        right_group.grid(
            row=self._layout["row"],
            column=self._layout["right_column"],
            sticky=self._layout["right_sticky"],
            padx=(self._layout["zero"], self._style["right_padx"]),
            pady=self._style["group_pady"],
        )

        self.back_button = self._button(
            left_group,
            text="",
            font=self._style["back_font"],
            background=self._colors["background"],
            foreground=self._colors["foreground"],
            active_background=self._colors["active"],
            active_foreground=self._colors["foreground"],
            border_width=self._layout["back_border_width"],
            command=on_back,
            padx=self._style["back_padx"],
            pady=self._style["back_pady"],
        )
        self.back_button.pack(
            side=self._layout["left_side"],
            padx=(self._layout["zero"], self._style["back_button_gap"]),
        )
        self.back_button.pack_forget()

        self._logo_image: tk.PhotoImage | None = None
        try:
            self._logo_image = tk.PhotoImage(file=LOGO_PATH)
        except tk.TclError as exc:
            print(f"[UI] Unable to load header logo: {exc}")

        if self._logo_image is not None:
            self.logo_label = tk.Label(
                left_group,
                image=self._logo_image,
                bg=self._colors["background"],
                bd=self._layout["zero"],
            )
            self.logo_label.pack(
                side=self._layout["left_side"],
                padx=(
                    self._layout["zero"],
                    self._style["logo_gap"],
                ),
            )

        self.title_label = tk.Label(
            left_group,
            textvariable=self.title_var,
            font=self._style["title_font"],
            bg=self._colors["background"],
            fg=self._colors["foreground"],
        )
        self.title_label.pack(side=self._layout["left_side"])

        self.freq_label = tk.Label(
            center_group,
            textvariable=self.frequency_var,
            font=self._style["frequency_font"],
            bg=self._colors["background"],
            fg=self._colors["foreground"],
            anchor=self._layout["center_anchor"],
        )
        self.freq_label.pack(expand=True)

        self.location_label = tk.Label(
            right_group,
            textvariable=self.location_var,
            font=self._style["location_font"],
            bg=self._colors["background"],
            fg=self._colors["foreground"],
            padx=self._style["location_padx"],
        )
        self.location_label.pack(
            side=self._layout["left_side"],
            padx=(self._layout["zero"], self._style["location_gap"]),
        )

        self.vol_down_button = self._button(
            right_group,
            text=self._layout["volume_down_text"],
            font=self._style["volume_button_font"],
            background=self._colors["volume_button_bg"],
            foreground=self._colors["volume_button_fg"],
            active_background=self._colors["active"],
            active_foreground=self._colors["volume_button_fg"],
            border_width=self._layout["button_border_width"],
            width=self._style["volume_button_width"],
            height=self._layout["button_height"],
            command=on_volume_down,
        )
        self.vol_down_button.pack(
            side=self._layout["left_side"],
            padx=(self._layout["zero"], self._style["volume_button_gap"]),
        )

        self.volume_indicator = VolumeIndicator(
            right_group,
            steps=volume_steps,
            initial_level=volume_level,
            initial_muted=volume_muted,
            style=VolumeIndicatorStyle(
                background=self._colors["background"],
                active=self._colors["volume_indicator_active"],
                inactive=self._colors["volume_indicator_inactive"],
                muted=self._colors["volume_indicator_muted"],
                bar_width=self._style["volume_bar_width"],
                base_height=self._style["volume_bar_base_height"],
                height_step=self._style["volume_bar_height_step"],
                bar_gap=self._style["volume_bar_gap"],
                anchor=self._layout["bottom_anchor"],
                side=self._layout["left_side"],
            ),
        )
        self.volume_indicator.pack(
            side=self._layout["left_side"],
            padx=(
                self._style["indicator_left_gap"],
                self._style["indicator_right_gap"],
            ),
        )

        self.vol_up_button = self._button(
            right_group,
            text=self._layout["volume_up_text"],
            font=self._style["volume_button_font"],
            background=self._colors["volume_button_bg"],
            foreground=self._colors["volume_button_fg"],
            active_background=self._colors["active"],
            active_foreground=self._colors["volume_button_fg"],
            border_width=self._layout["button_border_width"],
            width=self._style["volume_button_width"],
            height=self._layout["button_height"],
            command=on_volume_up,
        )
        self.vol_up_button.pack(
            side=self._layout["left_side"],
            padx=(self._layout["zero"], self._style["settings_gap"]),
        )

        self.settings_button = self._button(
            right_group,
            text=self._layout["settings_text"],
            font=self._style["settings_font"],
            background=self._colors["background"],
            foreground=self._colors["foreground"],
            active_background=self._colors["active"],
            active_foreground=self._colors["foreground"],
            border_width=self._layout["button_border_width"],
            width=self._style["control_button_width"],
            height=self._layout["button_height"],
            command=on_settings,
        )
        self.settings_button.pack(
            side=self._layout["left_side"],
            padx=(self._layout["zero"], self._style["settings_gap"]),
        )

        self.power_button = self._button(
            right_group,
            text=self._layout["power_text"],
            font=self._style["power_font"],
            background=self._colors["power_bg"],
            foreground=self._colors["power_fg"],
            active_background=self._colors["power_active"],
            active_foreground=self._colors["power_fg"],
            border_width=self._layout["button_border_width"],
            width=self._style["control_button_width"],
            height=self._layout["button_height"],
            command=on_power,
        )
        self.power_button.pack(side=self._layout["right_side"])

    def _button(
        self,
        parent: tk.Widget,
        *,
        text: str,
        font: Any,
        background: str,
        foreground: str,
        active_background: str,
        active_foreground: str,
        border_width: int,
        command: Callable[[], None],
        padx: int = 0,
        pady: int = 0,
        width: int | None = None,
        height: int | None = None,
    ) -> tk.Button:
        options: dict[str, Any] = {
            "text": text,
            "font": font,
            "bg": background,
            "fg": foreground,
            "activebackground": active_background,
            "activeforeground": active_foreground,
            "bd": border_width,
            "padx": padx,
            "pady": pady,
            "cursor": self._layout["cursor"],
            "command": command,
        }
        if width is not None:
            options["width"] = width
        if height is not None:
            options["height"] = height
        return tk.Button(parent, **options)
