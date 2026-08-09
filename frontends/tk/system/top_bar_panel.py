from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from os import PathLike
from typing import Any

from ui.system import TopBarUiIf


class TopBarPanel(tk.Frame, TopBarUiIf):
    """Render Car UI navigation, title, telemetry, and shell actions."""
    def __init__(
        self,
        parent: tk.Widget,
        *,
        compact_ui: bool,
        theme: dict[str, Any],
        logo_path: str | PathLike[str] | None,
        on_back: Callable[[], None],
        right_accessory_factory: Callable[[tk.Widget], tk.Widget] | None,
        on_settings: Callable[[], None],
        on_power: Callable[[], None],
    ) -> None:
        self._theme = theme
        self._colors = theme["colors"]
        self._layout = theme["layout"]
        self._style = theme["profiles"]["compact" if compact_ui else "normal"]
        self._compact_ui = compact_ui
        self._logo_path = logo_path

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
            right_accessory_factory=right_accessory_factory,
            on_settings=on_settings,
            on_power=on_power,
        )

    def show_back_button(self, text: str | None = None) -> None:
        self.back_button.config(text=text or self._layout["back_button_text"])
        self.back_button.pack(
            side=self._layout["left_side"],
            padx=(self._layout["zero"], self._style["back_button_gap"]),
        )

    def hide_back_button(self) -> None:
        self.back_button.pack_forget()

    def set_back_action(self, action: Callable[[], None]) -> None:
        self.back_button.config(command=action)

    def invoke_back_action(self) -> None:
        self.back_button.invoke()

    def set_title(self, title: str) -> None:
        if self._compact_ui:
            title = self._theme["compact_titles"].get(title, title)
        self.title_var.set(title)

    def set_frequency_text(self, text: str) -> None:
        self.frequency_var.set(text)

    def set_location_text(self, text: str) -> None:
        self.location_var.set(text)

    def _build(
        self,
        *,
        on_back: Callable[[], None],
        right_accessory_factory: Callable[[tk.Widget], tk.Widget] | None,
        on_settings: Callable[[], None],
        on_power: Callable[[], None],
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
        if self._logo_path is not None:
            try:
                self._logo_image = tk.PhotoImage(file=self._logo_path)
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

        if right_accessory_factory is not None:
            accessory = right_accessory_factory(right_group)
            accessory.pack(side=self._layout["left_side"])

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
