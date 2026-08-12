# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable, Optional

from frontends.tk.radio.radio_panel_config import RadioPanelConfig
from ui.radio.radio_formatter import (
    compact_preset_label,
    format_frequency,
    format_step,
)
from ui.radio import (
    PlaybackRequestHandlerIf,
    PresetRequestHandlerIf,
    RadioApplicationRequestHandlerIf,
    RadioPreset,
    RadioRefreshRequestHandlerIf,
    RadioUiIf,
    StationRequestHandlerIf,
    TunedSignal,
    TuningRequestHandlerIf,
)


class RadioPanel(tk.Frame, RadioUiIf):
    """Render radio state and emit semantic radio requests."""
    def __init__(
        self,
        parent: tk.Widget,
        panel_config: RadioPanelConfig,
        theme: dict[str, Any],
        on_frequency_changed: Optional[Callable[[int], None]] = None,
        presets_per_bank: int = 6,
    ) -> None:
        super().__init__(parent, bg=theme["colors"]["panel_bg"], takefocus=True)

        self.parent = parent
        self.panel_config = panel_config
        self.on_frequency_changed = on_frequency_changed
        self.compact_ui = bool(
            getattr(parent.winfo_toplevel(), "compact_ui", False)
        )
        self.theme = theme
        self.colors = self.theme["colors"]
        self.layout = self.theme["layout"]
        self.style = self.theme["profiles"][
            "compact" if self.compact_ui else "normal"
        ]

        self._presets: list[RadioPreset] = []
        self._receiver_active = False
        self._active_preset_index: int | None = None
        self._preset_handler: PresetRequestHandlerIf | None = None
        self._playback_handler: PlaybackRequestHandlerIf | None = None
        self._station_handler: StationRequestHandlerIf | None = None
        self._tuning_handler: TuningRequestHandlerIf | None = None
        self._application_handler: RadioApplicationRequestHandlerIf | None = None
        self._refresh_handler: RadioRefreshRequestHandlerIf | None = None

        self.preset_tiles: dict[int, tk.Frame] = {}
        self.active_preset_frequency_hz: Optional[int] = None

        self.presets_per_bank = max(1, presets_per_bank)
        self.preset_bank_index = 0
        self.preset_grid: Optional[tk.Frame] = None
        self.preset_bank_label_var = tk.StringVar(value="Bank 1/1")

        self.radio_status_widgets: dict[str, tk.Label] = {}
        self._status_poll_after_id: Optional[str] = None

        self._last_frequency_hz: Optional[int] = None

        self._build_panel(self)

    def start(self) -> None:
        """Request initial state and begin periodic telemetry refreshes."""
        self._request_refresh()
        self.start_radio_status_polling()

    def destroy(self) -> None:
        """Stop polling and destroy the Tk panel."""
        self.stop_radio_status_polling()
        super().destroy()

    def _build_panel(self, root: tk.Frame) -> None:
        root.columnconfigure(self.layout["root_column"], weight=self.layout["fill_weight"])
        root.rowconfigure(self.layout["content_row"], weight=self.layout["fill_weight"])
        root.rowconfigure(self.layout["status_row"], weight=self.layout["fixed_weight"])

        main = tk.Frame(root, bg=self.colors["panel_bg"])
        main.grid(row=self.layout["content_row"], column=self.layout["root_column"], sticky=self.layout["fill_sticky"])

        # Keep a stable left/right split on the 800x480 Pi display.
        # Without a uniform group, oversized control labels can force the
        # preset column into useless slivers. Because apparently widgets
        # demand territory now.
        left_weight, right_weight = self.style["main_column_weights"]
        main.columnconfigure(self.layout["control_column"], weight=left_weight, uniform=f"{self.panel_config.key}_main")
        main.columnconfigure(self.layout["preset_column"], weight=right_weight, uniform=f"{self.panel_config.key}_main")
        main.rowconfigure(self.layout["content_row"], weight=self.layout["fill_weight"])

        control_col = tk.Frame(main, bg=self.colors["panel_bg"])
        control_col.grid(row=self.layout["content_row"], column=self.layout["control_column"], sticky=self.layout["fill_sticky"], padx=(self.layout["zero"], self.style["column_gap"]))

        preset_area = tk.Frame(main, bg=self.colors["panel_bg"])
        preset_area.grid(row=self.layout["content_row"], column=self.layout["preset_column"], sticky=self.layout["fill_sticky"], padx=(self.style["column_gap"], self.layout["zero"]))
        preset_area.columnconfigure(self.layout["root_column"], weight=self.layout["fill_weight"])
        preset_area.rowconfigure(self.layout["content_row"], weight=self.layout["fill_weight"])
        preset_area.rowconfigure(self.layout["status_row"], weight=self.layout["fixed_weight"])

        self.preset_grid = tk.Frame(preset_area, bg=self.colors["panel_bg"])
        self.preset_grid.grid(row=self.layout["content_row"], column=self.layout["root_column"], sticky=self.layout["fill_sticky"])

        self._build_control_tiles(control_col)
        self._build_preset_tiles(self.preset_grid)
        self._build_preset_bank_nav(preset_area)
        self._build_status_row(root)

    def _build_control_tiles(self, parent: tk.Frame) -> None:
        parent.columnconfigure(self.layout["control_left_column"], weight=self.layout["fill_weight"], uniform=f"{self.panel_config.key}_control_col")
        parent.columnconfigure(self.layout["control_right_column"], weight=self.layout["fill_weight"], uniform=f"{self.panel_config.key}_control_col")

        for row in range(self.layout["control_row_count"]):
            parent.rowconfigure(row, weight=self.layout["fill_weight"], uniform=f"{self.panel_config.key}_control_row")

        step_label = format_step(self.panel_config.default_step_hz)

        controls = [
            (
                "toggle_app",
                "▶",
                self.panel_config.launch_tile.label,
                self.panel_config.launch_tile.subtitle,
                self.panel_config.launch_tile.detail,
                self._request_application_toggle,
            ),
            (
                "toggle_radio",
                "⏼",
                self.panel_config.radio_toggle_tile.label,
                self.panel_config.radio_toggle_tile.subtitle,
                self.panel_config.radio_toggle_tile.detail,
                self._request_playback_toggle,
            ),
            (
                "freq_down",
                "-",
                "Tune",
                "Down",
                f"Step: {step_label}",
                self._request_tune_down,
            ),
            (
                "freq_up",
                "+",
                "Tune",
                "Up",
                f"Step: {step_label}",
                self._request_tune_up,
            ),
            (
                "previous_preset",
                "←",
                "Preset",
                "Previous",
                "Cycle back",
                self._request_previous_station,
            ),
            (
                "next_preset",
                "→",
                "Preset →",
                "Next",
                "Cycle forward",
                self._request_next_station,
            ),
        ]

        for index, (key, icon, label, subtitle, detail, callback) in enumerate(controls):
            row = index // self.layout["control_column_count"]
            col = index % self.layout["control_column_count"]

            self._add_control_tile(
                parent=parent,
                row=row,
                col=col,
                key=key,
                icon=icon,
                label=label,
                subtitle=subtitle,
                detail=detail,
                callback=callback,
            )

    def _build_preset_tiles(self, parent: tk.Frame) -> None:
        self.preset_tiles.clear()

        for child in parent.winfo_children():
            child.destroy()

        all_presets = self._presets
        bank_count = self._preset_bank_count()
        self.preset_bank_index = min(self.preset_bank_index, bank_count - 1)

        start = self.preset_bank_index * self.presets_per_bank
        end = start + self.presets_per_bank
        presets = all_presets[start:end]

        cols = max(1, self.panel_config.preset_columns)
        rows = max(1, (len(presets) + cols - 1) // cols)

        for row in range(rows):
            parent.rowconfigure(row, weight=self.layout["fill_weight"], uniform=f"{self.panel_config.key}_preset_row")

        for col in range(cols):
            parent.columnconfigure(col, weight=self.layout["fill_weight"], uniform=f"{self.panel_config.key}_preset_col")

        precision = self.layout["fm_precision"] if self.panel_config.key == self.layout["fm_panel_key"] else self.layout["default_precision"]
        
        for index, preset in enumerate(presets):
            row = index // cols
            col = index % cols
            preset_number = start + index + 1

            tile = self._create_preset_tile(
                parent=parent,
                key=f"{self.panel_config.key}_preset_{preset.frequency_hz}",
                number=preset_number,
                frequency_text=compact_preset_label(preset, precision=precision),
                detail=preset.label,
            )
            self.preset_tiles[preset.frequency_hz] = tile
            preset_pad = self.style["preset_tile_pad"]
            tile.grid(row=row, column=col, sticky=self.layout["fill_sticky"], padx=preset_pad, pady=preset_pad)
            preset_index = start + index
            self._bind_click_recursive(
                tile,
                lambda selected=preset_index: self._request_preset(selected),
            )

        self._refresh_active_preset_tile()
        self._update_preset_bank_label()

    def _create_preset_tile(
        self,
        parent: tk.Widget,
        key: str,
        number: int,
        frequency_text: str,
        detail: str,
    ) -> tk.Frame:
        tile = tk.Frame(
            parent,
            bg=self.colors["tile_bg"],
            highlightthickness=self.style["tile_border_width"],
            highlightbackground=self.colors["tile_border"],
            highlightcolor=self.colors["primary_value"],
            bd=self.layout["border_width"],
            cursor=self.layout["interactive_cursor"],
        )
        tile.car_tile_kind = "preset"  # type: ignore[attr-defined]
        tile.car_tile_key = key  # type: ignore[attr-defined]

        tile.columnconfigure(self.layout["tile_column"], weight=self.layout["fill_weight"])
        tile.rowconfigure(self.layout["preset_number_row"], weight=self.layout["fixed_weight"])
        tile.rowconfigure(self.layout["preset_value_row"], weight=self.layout["fill_weight"])
        tile.rowconfigure(self.layout["preset_detail_row"], weight=self.layout["fixed_weight"])

        number_label = tk.Label(
            tile,
            text=f"#{number}",
            font=self.style["preset_number_font"],
            bg=self.colors["tile_bg"],
            fg=self.colors["primary_value"],
            anchor=self.layout["left_anchor"],
        )
        number_label.grid(
            row=self.layout["preset_number_row"],
            column=self.layout["tile_column"],
            sticky=self.layout["northwest_sticky"],
            padx=self.style["preset_number_padx"],
            pady=(self.style["preset_number_pady"], self.layout["zero"]),
        )

        freq_label = tk.Label(
            tile,
            text=frequency_text,
            font=self.style["preset_frequency_font"],
            bg=self.colors["tile_bg"],
            fg=self.colors["tile_title"],
            anchor=self.layout["center_anchor"],
        )
        freq_label.grid(
            row=self.layout["preset_value_row"],
            column=self.layout["tile_column"],
            sticky=self.layout["fill_sticky"],
            padx=self.style["preset_value_padx"],
            pady=self.layout["zero_padding"],
        )

        detail_label = tk.Label(
            tile,
            text=detail,
            font=self.style["preset_detail_font"],
            bg=self.colors["tile_bg"],
            fg=self.colors["tile_subtitle"],
            anchor=self.layout["center_anchor"],
        )
        detail_label.grid(
            row=self.layout["preset_detail_row"],
            column=self.layout["tile_column"],
            sticky=self.layout["horizontal_sticky"],
            padx=self.style["preset_detail_padx"],
            pady=(self.layout["zero"], self.style["preset_detail_pady"]),
        )

        return tile

    def _build_preset_bank_nav(self, parent: tk.Frame) -> None:
        nav = tk.Frame(parent, bg=self.colors["panel_bg"])
        nav.grid(row=self.layout["bank_nav_row"], column=self.layout["root_column"], sticky=self.layout["horizontal_sticky"], pady=(self.style["bank_nav_top_pad"], self.layout["zero"]))

        for column in range(self.layout["bank_column_count"]):
            nav.columnconfigure(column, weight=self.layout["fill_weight"])

        prev_button = tk.Button(
            nav,
            text="◀ Bank",
            font=self.style["bank_button_font"],
            bg=self.colors["bank_button_bg"],
            fg=self.colors["bank_button_fg"],
            activebackground=self.colors["bank_button_active_bg"],
            activeforeground=self.colors["bank_button_active_fg"],
            bd=self.layout["border_width"],
            padx=self.style["bank_button_padx"],
            pady=self.style["bank_button_pady"],
            command=self.previous_preset_bank,
            cursor=self.layout["interactive_cursor"],
        )
        prev_button.grid(row=self.layout["nav_row"], column=self.layout["bank_previous_column"], sticky=self.layout["horizontal_sticky"], padx=(self.layout["zero"], self.style["bank_button_gap"]))

        label = tk.Label(
            nav,
            textvariable=self.preset_bank_label_var,
            font=self.style["bank_button_font"],
            bg=self.colors["panel_bg"],
            fg=self.colors["primary_value"],
            anchor=self.layout["center_anchor"],
            padx=self.style["bank_label_padx"],
        )
        label.grid(row=self.layout["nav_row"], column=self.layout["bank_label_column"], sticky=self.layout["horizontal_sticky"])

        next_button = tk.Button(
            nav,
            text="Bank ▶",
            font=self.style["bank_button_font"],
            bg=self.colors["bank_button_bg"],
            fg=self.colors["bank_button_fg"],
            activebackground=self.colors["bank_button_active_bg"],
            activeforeground=self.colors["bank_button_active_fg"],
            bd=self.layout["border_width"],
            padx=self.style["bank_button_padx"],
            pady=self.style["bank_button_pady"],
            command=self.next_preset_bank,
            cursor=self.layout["interactive_cursor"],
        )
        next_button.grid(row=self.layout["nav_row"], column=self.layout["bank_next_column"], sticky=self.layout["horizontal_sticky"], padx=(self.style["bank_button_gap"], self.layout["zero"]))

    def previous_preset_bank(self) -> None:
        """Display the previous page of presets."""
        bank_count = self._preset_bank_count()
        self.preset_bank_index = (self.preset_bank_index - 1) % bank_count
        self._refresh_preset_bank()

    def next_preset_bank(self) -> None:
        """Display the next page of presets."""
        bank_count = self._preset_bank_count()
        self.preset_bank_index = (self.preset_bank_index + 1) % bank_count
        self._refresh_preset_bank()

    def _refresh_preset_bank(self) -> None:
        if self.preset_grid is None:
            return

        self._build_preset_tiles(self.preset_grid)

    def _preset_bank_count(self) -> int:
        total = len(self._presets)
        return max(1, (total + self.presets_per_bank - 1) // self.presets_per_bank)

    def _update_preset_bank_label(self) -> None:
        self.preset_bank_label_var.set(
            f"Bank {self.preset_bank_index + 1}/{self._preset_bank_count()}"
        )

    def _add_control_tile(
        self,
        parent: tk.Frame,
        row: int,
        col: int,
        key: str,
        icon: str,
        label: str,
        subtitle: str,
        detail: str,
        callback: Callable[[], None],
    ) -> None:
        tile = self._create_control_tile(
            parent=parent,
            key=f"{self.panel_config.key}_{key}",
            icon=icon,
            label=label,
            subtitle=subtitle,
            detail=detail,
        )
        control_pad = self.style["control_tile_pad"]
        tile.grid(row=row, column=col, sticky=self.layout["fill_sticky"], padx=control_pad, pady=control_pad)
        self._bind_click_recursive(tile, callback)

    def _create_control_tile(
        self,
        parent: tk.Widget,
        key: str,
        icon: str,
        label: str,
        subtitle: str,
        detail: str,
    ) -> tk.Frame:
        tile = tk.Frame(
            parent,
            bg=self.colors["tile_bg"],
            highlightthickness=self.style["tile_border_width"],
            highlightbackground=self.colors["tile_border"],
            highlightcolor=self.colors["primary_value"],
            bd=self.layout["border_width"],
            cursor=self.layout["interactive_cursor"],
        )
        tile.car_tile_kind = "control"  # type: ignore[attr-defined]
        tile.car_tile_key = key  # type: ignore[attr-defined]

        accent = tk.Frame(
            tile,
            bg=self.colors["control_accent"],
            height=self.style["control_accent_height"],
        )
        accent.pack(fill=self.layout["horizontal_fill"], side=self.layout["top_side"])

        body = tk.Frame(tile, bg=self.colors["tile_bg"])
        body.pack(
            fill=self.layout["both_fill"],
            expand=self.layout["expand"],
            padx=self.style["control_body_padx"],
            pady=self.style["control_body_pady"],
        )

        body.columnconfigure(self.layout["icon_column"], weight=self.layout["fixed_weight"])
        body.columnconfigure(self.layout["text_column"], weight=self.layout["fill_weight"])
        body.rowconfigure(self.layout["body_row"], weight=self.layout["fill_weight"])

        icon_label = tk.Label(
            body,
            text=icon,
            font=self.style["control_icon_font"],
            bg=self.colors["tile_bg"],
            fg=self.colors["primary_value"],
            width=self.style["control_icon_width"],
            anchor=self.layout["center_anchor"],
        )
        icon_label.grid(
            row=self.layout["body_row"],
            column=self.layout["icon_column"],
            sticky=self.layout["north_sticky"],
            padx=(self.layout["zero"], self.style["control_icon_gap"]),
            pady=(self.style["control_icon_pady"], self.layout["zero"]),
        )

        text_area = tk.Frame(body, bg=self.colors["tile_bg"])
        text_area.grid(row=self.layout["body_row"], column=self.layout["text_column"], sticky=self.layout["fill_sticky"])

        title = tk.Label(
            text_area,
            text=label,
            font=self.style["control_title_font"],
            bg=self.colors["tile_bg"],
            fg=self.colors["tile_title"],
            anchor=self.layout["left_anchor"],
            justify=self.layout["left_justify"],
            wraplength=self.style["control_text_wrap"],
        )
        title.pack(fill=self.layout["horizontal_fill"], anchor=self.layout["left_anchor"])

        subtitle_label = tk.Label(
            text_area,
            text=subtitle,
            font=self.style["control_subtitle_font"],
            bg=self.colors["tile_bg"],
            fg=self.colors["tile_subtitle"],
            anchor=self.layout["left_anchor"],
            justify=self.layout["left_justify"],
            wraplength=self.style["control_text_wrap"],
        )
        subtitle_label.pack(fill=self.layout["horizontal_fill"], anchor=self.layout["left_anchor"], pady=(self.style["control_subtitle_pady"], self.layout["zero"]))

        detail_label = tk.Label(
            text_area,
            text=detail,
            font=self.style["control_detail_font"],
            bg=self.colors["tile_bg"],
            fg=self.colors["tile_detail"],
            anchor=self.layout["left_anchor"],
            justify=self.layout["left_justify"],
            wraplength=self.style["control_text_wrap"],
        )
        detail_label.pack(fill=self.layout["horizontal_fill"], anchor=self.layout["left_anchor"], pady=(self.style["control_detail_pady"], self.layout["zero"]))

        return tile

    def _build_status_row(self, parent: tk.Frame) -> None:
        status = tk.Frame(parent, bg=self.colors["status_bg"])
        status.grid(
            row=self.layout["status_row"],
            column=self.layout["root_column"],
            sticky=self.layout["horizontal_sticky"],
            pady=(self.style["status_top_pad"], self.layout["zero"]),
            ipady=self.style["status_ipady"],
        )

        fields = [
            ("frequency", "Freq:", self.layout["empty_value"], self.colors["primary_value"]),
            ("preset", "Preset:", self.layout["empty_value"], self.colors["primary_value"]),
            ("mode", "Mode:", self.layout["empty_value"], self.colors["primary_value"]),
            ("signal", "Signal:", "--", self.colors["telemetry_value"]),
            ("snr", "SNR:", "--", self.colors["telemetry_value"]),
            ("rds", "RDS:", self.layout["empty_value"], self.colors["telemetry_value"]),
        ]

        for col in range(len(fields)):
            status.columnconfigure(col, weight=self.layout["fill_weight"])

        for col, (key, label_text, value_text, value_fg) in enumerate(fields):
            group = tk.Frame(status, bg=self.colors["status_bg"])
            group.grid(
                row=self.layout["status_content_row"],
                column=col,
                sticky=self.layout["fill_sticky"],
                padx=self.style["status_group_padx"],
            )

            label = tk.Label(
                group,
                text=label_text,
                bg=self.colors["status_bg"],
                fg=self.colors["status_label"],
                font=self.style["status_font"],
            )
            label.pack(side=self.layout["left_side"])

            value = tk.Label(
                group,
                text=value_text,
                bg=self.colors["status_bg"],
                fg=value_fg,
                font=self.style["status_font"],
            )
            value.pack(side=self.layout["left_side"], padx=(self.style["bank_button_gap"], self.layout["zero"]))

            self.radio_status_widgets[key] = value

    def set_signal(self, signal: TunedSignal | None) -> None:
        """Render the current tuned signal and telemetry."""
        empty = self.layout["empty_value"]

        if signal is None:
            self._set_radio_status_value("frequency", empty)
            self._set_radio_status_value("mode", empty)
            self._set_radio_status_value("signal", empty)
            self._set_radio_status_value("snr", empty)
            self._set_radio_status_value("rds", empty)
            return
        else:
            self._set_radio_status_value(
                "frequency",
                format_frequency(signal.frequency_hz),
            )
            if (
                self.on_frequency_changed is not None
                and signal.frequency_hz != self._last_frequency_hz
            ):
                self._last_frequency_hz = signal.frequency_hz
                self.on_frequency_changed(signal.frequency_hz)

        self._set_radio_status_value("mode", signal.mode.modulation.name)
        self._set_radio_status_value(
            "signal",
            self._format_status_value(signal.signal_strength_dbfs),
        )
        self._set_radio_status_value(
            "snr",
            self._format_status_value(signal.snr_db),
        )
        self._set_radio_status_value("rds", signal.rds_text or empty)

    def add_preset(self, preset: RadioPreset) -> None:
        self._presets.append(preset)
        if self.preset_grid is not None:
            self._refresh_preset_bank()

    def clear_presets(self) -> None:
        self._presets.clear()
        self._active_preset_index = None
        if self.preset_grid is not None:
            self._refresh_preset_bank()

    def set_receiver_active(self, active: bool) -> None:
        self._receiver_active = bool(active)

    def set_active_preset(self, preset_index: int | None) -> None:
        self._active_preset_index = preset_index
        if preset_index is None or not 0 <= preset_index < len(self._presets):
            self._set_radio_status_value("preset", self.layout["empty_value"])
            self._clear_active_preset_tile()
            return
        preset = self._presets[preset_index]
        self._set_radio_status_value(
            "preset", f"{preset_index + 1}/{len(self._presets)}"
        )
        self._set_active_preset_tile(preset)
        self._ensure_preset_bank_visible(preset_index)

    def set_preset_request_handler(
        self, handler: PresetRequestHandlerIf | None
    ) -> None:
        self._preset_handler = handler

    def set_playback_request_handler(
        self, handler: PlaybackRequestHandlerIf | None
    ) -> None:
        self._playback_handler = handler

    def set_station_request_handler(
        self, handler: StationRequestHandlerIf | None
    ) -> None:
        self._station_handler = handler

    def set_tuning_request_handler(
        self, handler: TuningRequestHandlerIf | None
    ) -> None:
        self._tuning_handler = handler

    def set_application_request_handler(
        self, handler: RadioApplicationRequestHandlerIf | None
    ) -> None:
        self._application_handler = handler

    def set_refresh_request_handler(
        self, handler: RadioRefreshRequestHandlerIf | None
    ) -> None:
        self._refresh_handler = handler

    def _format_status_value(self, value: object | None) -> str:
        if value is None:
            return self.layout["empty_value"]
        return str(value)

    def _bind_click_recursive(self, widget: tk.Widget, callback: Callable[[], None]) -> None:
        widget.bind("<Button-1>", lambda event: callback())

        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback)

    def _set_active_preset_tile(self, preset: RadioPreset) -> None:
        self.active_preset_frequency_hz = preset.frequency_hz
        self._refresh_active_preset_tile()

    def _refresh_active_preset_tile(self) -> None:
        for frequency_hz, tile in self.preset_tiles.items():
            active = frequency_hz == self.active_preset_frequency_hz
            self._set_tile_active(tile, active)

    def _set_tile_active(self, tile: tk.Widget, active: bool) -> None:
        kind = getattr(tile, "car_tile_kind", "")
        if kind != "preset":
            return

        bg = self.colors["active_preset_bg"] if active else self.colors["tile_bg"]
        border = (
            self.colors["active_preset_border"]
            if active
            else self.colors["tile_border"]
        )
        freq_fg = (
            self.colors["active_preset_fg"]
            if active
            else self.colors["tile_title"]
        )
        detail_fg = (
            self.colors["active_preset_fg"]
            if active
            else self.colors["tile_subtitle"]
        )

        try:
            tile.configure(bg=bg, highlightbackground=border, highlightcolor=border)
        except tk.TclError:
            pass

        for child in tile.winfo_children():
            if not isinstance(child, tk.Label):
                continue

            text = str(child.cget("text"))
            try:
                if text.startswith("#"):
                    child.configure(bg=bg, fg=self.colors["primary_value"])
                elif text == "" or text is None:
                    child.configure(bg=bg)
                elif self._looks_like_frequency_label(text):
                    child.configure(bg=bg, fg=freq_fg)
                else:
                    child.configure(bg=bg, fg=detail_fg)
            except tk.TclError:
                pass

    @staticmethod
    def _looks_like_frequency_label(text: str) -> bool:
        return any(ch.isdigit() for ch in text) and not text.startswith("#")

    def _ensure_preset_bank_visible(self, preset_index: int) -> None:
        wanted_bank_index = preset_index // self.presets_per_bank
        if wanted_bank_index == self.preset_bank_index:
            return

        self.preset_bank_index = wanted_bank_index
        self._refresh_preset_bank()

    def _clear_active_preset_tile(self) -> None:
        self.active_preset_frequency_hz = None

        for tile in self.preset_tiles.values():
            self._set_tile_active(tile, False)

    def _set_radio_status_value(self, key: str, value: str) -> None:
        widget = self.radio_status_widgets.get(key)
        if widget is not None:
            widget.config(text=value)

    def start_radio_status_polling(self, interval_ms: int | None = None) -> None:
        """Begin periodic state refreshes at ``interval_ms``."""
        if interval_ms is None:
            interval_ms = self.layout["poll_interval_ms"]
        self.stop_radio_status_polling()
        self._poll_radio_status(interval_ms)

    def stop_radio_status_polling(self) -> None:
        """Cancel periodic radio-state refreshes."""
        if self._status_poll_after_id is None:
            return

        try:
            self.parent.after_cancel(self._status_poll_after_id)
        except Exception:
            pass

        self._status_poll_after_id = None

    def _poll_radio_status(self, interval_ms: int) -> None:
        if not self.winfo_exists():
            return

        self._request_refresh()

        self._status_poll_after_id = self.parent.after(
            interval_ms,
            lambda: self._poll_radio_status(interval_ms),
        )

    def _request_application_toggle(self) -> None:
        if self._application_handler is not None:
            self._application_handler.request_toggle_radio_application()

    def _request_playback_toggle(self) -> None:
        if self._playback_handler is None:
            return
        if self._receiver_active:
            self._playback_handler.request_pause()
        else:
            self._playback_handler.request_play()

    def _request_tune_up(self) -> None:
        if self._tuning_handler is not None:
            self._tuning_handler.request_tune_up()

    def _request_tune_down(self) -> None:
        if self._tuning_handler is not None:
            self._tuning_handler.request_tune_down()

    def _request_next_station(self) -> None:
        if self._station_handler is not None:
            self._station_handler.request_next_station()

    def _request_previous_station(self) -> None:
        if self._station_handler is not None:
            self._station_handler.request_previous_station()

    def _request_preset(self, preset_index: int) -> None:
        if self._preset_handler is not None:
            self._preset_handler.request_preset(preset_index)

    def _request_refresh(self) -> None:
        if self._refresh_handler is not None:
            self._refresh_handler.request_radio_refresh()
