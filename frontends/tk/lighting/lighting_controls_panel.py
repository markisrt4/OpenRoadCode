from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from ui.lighting import (
    LightingColor,
    LightingRequestHandlerIf,
    LightingState,
)


class LightingControlsPanel(tk.Frame):
    """Render lighting state and emit semantic lighting requests."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        theme: dict[str, Any],
    ) -> None:
        self._handler: LightingRequestHandlerIf | None = None
        self._theme = theme
        self._colors = theme["colors"]
        self._layout = theme["layout"]
        self._style = theme["profiles"]["default"]
        self._presets = theme["color_presets"]
        self._patterns = theme["patterns"]
        self._music_modes = theme["music_modes"]

        super().__init__(parent, bg=self._colors["background"])

        initial_brightness = self._layout["initial_brightness"]
        self._brightness = tk.IntVar(value=initial_brightness)
        self._brightness_text = tk.StringVar(
            value=f"{initial_brightness}%"
        )
        self._status = tk.StringVar(value=self._layout["connecting_text"])
        self._pattern_name = tk.StringVar(value=self._patterns[0][0])
        self._music_name = tk.StringVar(value=self._music_modes[0][0])
        self._brightness_after_id: str | None = None
        self._status_label: tk.Label | None = None

        self._build_ui()

    def set_lighting_request_handler(
        self,
        handler: LightingRequestHandlerIf | None,
    ) -> None:
        self._handler = handler

    def set_lighting_state(self, state: LightingState | None) -> None:
        if state is None:
            self._set_status(self._layout["connecting_text"], self._colors["muted_text"])
            return

        if state.error_message:
            self._set_status(state.error_message, self._colors["error"])
        else:
            self._set_status(
                state.status_message
                or (
                    self._layout["connected_text"]
                    if state.connected
                    else self._layout["connecting_text"]
                ),
                self._colors["ok"] if state.connected else self._colors["muted_text"],
            )
        self._brightness.set(state.brightness_percent)
        self._brightness_text.set(f"{state.brightness_percent}%")

    def _build_ui(self) -> None:
        self.columnconfigure(
            self._layout["main_column"],
            weight=self._layout["fill_weight"],
        )
        self.rowconfigure(
            self._layout["body_row"],
            weight=self._layout["fill_weight"],
        )

        header = tk.Frame(self, bg=self._colors["background"])
        header.grid(
            row=self._layout["header_row"],
            column=self._layout["main_column"],
            sticky=self._layout["horizontal_sticky"],
            padx=self._style["outer_padx"],
            pady=self._style["header_pady"],
        )
        header.columnconfigure(
            self._layout["header_title_column"],
            weight=self._layout["fill_weight"],
        )

        tk.Label(
            header,
            text=self._layout["title"],
            bg=self._colors["background"],
            fg=self._colors["text"],
            font=self._style["title_font"],
        ).grid(
            row=self._layout["row_zero"],
            column=self._layout["header_title_column"],
            sticky=self._layout["left_sticky"],
        )

        self._status_label = tk.Label(
            header,
            textvariable=self._status,
            bg=self._colors["background"],
            fg=self._colors["muted_text"],
            font=self._style["status_font"],
        )
        self._status_label.grid(
            row=self._layout["row_zero"],
            column=self._layout["header_status_column"],
            sticky=self._layout["right_sticky"],
        )

        power = self._section(self, self._layout["power_title"])
        power.grid(
            row=self._layout["power_row"],
            column=self._layout["main_column"],
            sticky=self._layout["horizontal_sticky"],
            padx=self._style["outer_padx"],
            pady=self._style["section_gap"],
        )
        for column in range(self._layout["power_columns"]):
            power.columnconfigure(column, weight=self._layout["fill_weight"])

        self._button(
            power,
            self._layout["power_on_text"],
            lambda: self._request(
                lambda handler: handler.request_power(True),
            ),
        ).grid(
            row=self._layout["control_row"],
            column=self._layout["left_column"],
            sticky=self._layout["horizontal_sticky"],
            padx=(self._layout["zero"], self._style["split_gap"]),
            pady=self._style["button_pady"],
            ipady=self._style["power_button_ipady"],
        )

        self._button(
            power,
            self._layout["power_off_text"],
            lambda: self._request(
                lambda handler: handler.request_power(False),
            ),
        ).grid(
            row=self._layout["control_row"],
            column=self._layout["right_column"],
            sticky=self._layout["horizontal_sticky"],
            padx=(self._style["split_gap"], self._layout["zero"]),
            pady=self._style["button_pady"],
            ipady=self._style["power_button_ipady"],
        )

        body = tk.Frame(self, bg=self._colors["background"])
        body.grid(
            row=self._layout["body_row"],
            column=self._layout["main_column"],
            sticky=self._layout["fill_sticky"],
            padx=self._style["outer_padx"],
            pady=self._style["body_pady"],
        )
        body.columnconfigure(
            self._layout["left_column"],
            weight=self._layout["fill_weight"],
        )
        body.columnconfigure(
            self._layout["right_column"],
            weight=self._layout["fill_weight"],
        )
        body.rowconfigure(
            self._layout["row_zero"],
            weight=self._layout["fill_weight"],
        )

        left = tk.Frame(body, bg=self._colors["background"])
        left.grid(
            row=self._layout["row_zero"],
            column=self._layout["left_column"],
            sticky=self._layout["fill_sticky"],
            padx=(self._layout["zero"], self._style["split_gap"]),
        )
        left.columnconfigure(
            self._layout["main_column"],
            weight=self._layout["fill_weight"],
        )

        right = tk.Frame(body, bg=self._colors["background"])
        right.grid(
            row=self._layout["row_zero"],
            column=self._layout["right_column"],
            sticky=self._layout["fill_sticky"],
            padx=(self._style["split_gap"], self._layout["zero"]),
        )
        right.columnconfigure(
            self._layout["main_column"],
            weight=self._layout["fill_weight"],
        )

        self._build_brightness(left).grid(
            row=self._layout["row_zero"],
            column=self._layout["main_column"],
            sticky=self._layout["horizontal_sticky"],
            pady=(self._layout["zero"], self._style["section_bottom_gap"]),
        )
        self._build_colors(left).grid(
            row=self._layout["colors_row"],
            column=self._layout["main_column"],
            sticky=self._layout["fill_sticky"],
        )
        self._build_modes(right).grid(
            row=self._layout["row_zero"],
            column=self._layout["main_column"],
            sticky=self._layout["fill_sticky"],
        )

    def _build_brightness(self, parent: tk.Misc) -> tk.Frame:
        frame = self._section(parent, self._layout["brightness_title"])
        frame.columnconfigure(
            self._layout["left_column"],
            weight=self._layout["fill_weight"],
        )

        tk.Label(
            frame,
            textvariable=self._brightness_text,
            bg=self._colors["card_background"],
            fg=self._colors["accent"],
            font=self._style["brightness_font"],
        ).grid(
            row=self._layout["row_zero"],
            column=self._layout["right_column"],
            sticky=self._layout["right_sticky"],
            padx=(self._style["split_gap"], self._layout["zero"]),
        )

        scale = tk.Scale(
            frame,
            from_=self._layout["brightness_min"],
            to=self._layout["brightness_max"],
            orient=self._layout["horizontal_orientation"],
            variable=self._brightness,
            command=self._on_brightness_changed,
            bg=self._colors["card_background"],
            fg=self._colors["text"],
            troughcolor=self._colors["accent_dark"],
            activebackground=self._colors["accent"],
            highlightthickness=self._layout["zero"],
            bd=self._layout["zero"],
            length=self._style["brightness_length"],
            showvalue=False,
        )
        scale.grid(
            row=self._layout["brightness_scale_row"],
            column=self._layout["left_column"],
            columnspan=self._layout["brightness_columnspan"],
            sticky=self._layout["horizontal_sticky"],
            pady=self._style["brightness_scale_pady"],
        )
        return frame

    def _build_colors(self, parent: tk.Misc) -> tk.Frame:
        frame = self._section(parent, self._layout["colors_title"])
        columns = self._layout["color_columns"]

        for column in range(columns):
            frame.columnconfigure(column, weight=self._layout["fill_weight"])

        for index, preset in enumerate(self._presets):
            name = preset["name"]
            color_hex = preset["hex"]
            rgb = LightingColor(*preset["rgb"])
            row = (index // columns) + self._layout["color_start_row"]
            column = index % columns
            foreground = (
                self._colors["light_button_text"]
                if preset.get("use_dark_text", False)
                else self._colors["text"]
            )

            tk.Button(
                frame,
                text=name,
                bg=color_hex,
                fg=foreground,
                activebackground=color_hex,
                activeforeground=foreground,
                relief=self._layout["flat_relief"],
                bd=self._layout["zero"],
                font=self._style["color_button_font"],
                cursor=self._layout["cursor"],
                command=lambda c=rgb: self._request(
                    lambda handler: handler.request_color(c),
                ),
            ).grid(
                row=row,
                column=column,
                sticky=self._layout["horizontal_sticky"],
                padx=self._style["color_button_padx"],
                pady=self._style["color_button_pady"],
                ipady=self._style["color_button_ipady"],
            )

        return frame

    def _build_modes(self, parent: tk.Misc) -> tk.Frame:
        frame = self._section(parent, self._layout["modes_title"])
        frame.columnconfigure(
            self._layout["main_column"],
            weight=self._layout["fill_weight"],
        )

        self._mode_label(
            frame,
            self._layout["effect_label"],
            self._layout["effect_label_row"],
            self._style["effect_label_pady"],
        )

        pattern = ttk.Combobox(
            frame,
            textvariable=self._pattern_name,
            values=[name for name, _ in self._patterns],
            state=self._layout["readonly_state"],
            font=self._style["combobox_font"],
        )
        pattern.grid(
            row=self._layout["effect_combo_row"],
            column=self._layout["main_column"],
            sticky=self._layout["horizontal_sticky"],
            ipady=self._style["combobox_ipady"],
        )
        pattern.bind(
            self._layout["combobox_event"],
            lambda _event: self._on_pattern_selected(),
        )

        self._mode_label(
            frame,
            self._layout["music_label"],
            self._layout["music_label_row"],
            self._style["music_label_pady"],
        )

        music = ttk.Combobox(
            frame,
            textvariable=self._music_name,
            values=[name for name, _ in self._music_modes],
            state=self._layout["readonly_state"],
            font=self._style["combobox_font"],
        )
        music.grid(
            row=self._layout["music_combo_row"],
            column=self._layout["main_column"],
            sticky=self._layout["horizontal_sticky"],
            ipady=self._style["combobox_ipady"],
        )
        music.bind(
            self._layout["combobox_event"],
            lambda _event: self._on_music_selected(),
        )

        quick = tk.Frame(frame, bg=self._colors["card_background"])
        quick.grid(
            row=self._layout["quick_row"],
            column=self._layout["main_column"],
            sticky=self._layout["horizontal_sticky"],
            pady=self._style["quick_pady"],
        )
        for column in range(self._layout["quick_columns"]):
            quick.columnconfigure(column, weight=self._layout["fill_weight"])

        self._button(
            quick,
            self._layout["rainbow_text"],
            lambda: self._set_pattern_by_name(
                self._layout["rainbow_pattern"]
            ),
        ).grid(
            row=self._layout["row_zero"],
            column=self._layout["left_column"],
            sticky=self._layout["horizontal_sticky"],
            padx=(self._layout["zero"], self._style["quick_gap"]),
            ipady=self._style["quick_button_ipady"],
        )

        self._button(
            quick,
            self._layout["strobe_text"],
            lambda: self._set_pattern_by_name(
                self._layout["strobe_pattern"]
            ),
        ).grid(
            row=self._layout["row_zero"],
            column=self._layout["right_column"],
            sticky=self._layout["horizontal_sticky"],
            padx=(self._style["quick_gap"], self._layout["zero"]),
            ipady=self._style["quick_button_ipady"],
        )

        return frame

    def _mode_label(
        self,
        parent: tk.Misc,
        text: str,
        row: int,
        pady: tuple[int, int],
    ) -> None:
        tk.Label(
            parent,
            text=text,
            bg=self._colors["card_background"],
            fg=self._colors["muted_text"],
            font=self._style["mode_label_font"],
        ).grid(
            row=row,
            column=self._layout["main_column"],
            sticky=self._layout["left_sticky"],
            pady=pady,
        )

    def _section(self, parent: tk.Misc, title: str) -> tk.Frame:
        frame = tk.Frame(
            parent,
            bg=self._colors["card_background"],
            padx=self._style["section_padx"],
            pady=self._style["section_pady"],
            highlightbackground=self._colors["card_border"],
            highlightcolor=self._colors["card_border"],
            highlightthickness=self._layout["card_border_width"],
            bd=self._layout["zero"],
        )
        tk.Label(
            frame,
            text=title,
            bg=self._colors["card_background"],
            fg=self._colors["text"],
            font=self._style["section_title_font"],
        ).grid(
            row=self._layout["row_zero"],
            column=self._layout["main_column"],
            sticky=self._layout["left_sticky"],
            columnspan=self._layout["section_columnspan"],
        )
        return frame

    def _button(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=self._colors["accent_dark"],
            fg=self._colors["text"],
            activebackground=self._colors["accent"],
            activeforeground=self._colors["text"],
            relief=self._layout["flat_relief"],
            bd=self._layout["zero"],
            font=self._style["button_font"],
            cursor=self._layout["cursor"],
        )

    def _on_brightness_changed(self, value: str) -> None:
        brightness = int(float(value))
        self._brightness.set(brightness)
        self._brightness_text.set(f"{brightness}%")

        if self._brightness_after_id is not None:
            self.after_cancel(self._brightness_after_id)

        self._brightness_after_id = self.after(
            self._layout["brightness_debounce_ms"],
            lambda b=brightness: self._request(
                lambda handler: handler.request_brightness(b),
            ),
        )

    def _on_pattern_selected(self) -> None:
        selected = self._pattern_name.get()
        for name, index in self._patterns:
            if name == selected:
                self._request(
                    lambda handler, value=index: handler.request_pattern(value),
                )
                return

    def _on_music_selected(self) -> None:
        selected = self._music_name.get()
        for name, index in self._music_modes:
            if name == selected:
                self._request(
                    lambda handler, value=index: handler.request_music_mode(value),
                )
                return

    def _set_pattern_by_name(self, name: str) -> None:
        self._pattern_name.set(name)
        self._on_pattern_selected()

    def _request(
        self,
        request: Callable[[LightingRequestHandlerIf], None],
    ) -> None:
        self._set_status(
            self._layout["working_text"],
            self._colors["muted_text"],
        )
        handler = self._handler
        if handler is None:
            return
        try:
            request(handler)
        except Exception as exc:
            self._set_status(
                f"Lighting request failed: {exc}",
                self._colors["error"],
            )

    def _set_status(self, text: str, color: str) -> None:
        self._status.set(text)
        if self._status_label is not None:
            self._status_label.configure(fg=color)

    def destroy(self) -> None:
        if self._brightness_after_id is not None:
            try:
                self.after_cancel(self._brightness_after_id)
            except tk.TclError:
                pass
            self._brightness_after_id = None

        super().destroy()
