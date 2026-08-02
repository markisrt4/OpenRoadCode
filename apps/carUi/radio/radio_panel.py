from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from apps.carUi.radio.radio_panel_config import RadioPanelConfig
from apps.carUi.radio.radio_session_controller import RadioSessionController
from apps.carUi.radio.radio_panel_state import RadioPanelState
from apps.carUi.radio.radio_status_formatter import (
    compact_preset_label,
    format_frequency,
    format_step,
)
from apps.common.uiTheme import RADIO_PANEL_THEME
from controllers.radio.radio_types import RadioPreset


class RadioPanel(tk.Frame):
    """Render radio controls and telemetry for a radio session."""
    def __init__(
        self,
        parent: tk.Widget,
        controller: RadioSessionController,
        panel_config: RadioPanelConfig,
        on_frequency_changed: Optional[Callable[[int], None]] = None,
        presets_per_bank: int = 6,
    ) -> None:
        super().__init__(parent, bg=RADIO_PANEL_THEME["colors"]["panel_bg"], takefocus=True)

        self.parent = parent
        self.panel_config = panel_config
        self.on_frequency_changed = on_frequency_changed
        self.compact_ui = bool(
            getattr(parent.winfo_toplevel(), "compact_ui", False)
        )
        self.theme = RADIO_PANEL_THEME
        self.colors = self.theme["colors"]
        self.layout = self.theme["layout"]
        self.style = self.theme["profiles"][
            "compact" if self.compact_ui else "normal"
        ]

        self.controller = controller
        self.controller.set_state_listener(self.render_state)

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
        """Begin rendering controller state and polling radio telemetry."""
        self.controller.refresh_state(include_telemetry=False)
        self.controller.report_ready()
        self.start_radio_status_polling()

    def destroy(self) -> None:
        """Stop polling and destroy the Tk panel."""
        self.stop_radio_status_polling()
        self.controller.set_state_listener(None)
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
                self.controller.toggle_radio_app,
            ),
            (
                "toggle_radio",
                "⏼",
                self.panel_config.radio_toggle_tile.label,
                self.panel_config.radio_toggle_tile.subtitle,
                self.panel_config.radio_toggle_tile.detail,
                self.controller.toggle_radio,
            ),
            (
                "freq_down",
                "-",
                "Tune",
                "Down",
                f"Step: {step_label}",
                self.controller.frequency_down,
            ),
            (
                "freq_up",
                "+",
                "Tune",
                "Up",
                f"Step: {step_label}",
                self.controller.frequency_up,
            ),
            (
                "previous_preset",
                "←",
                "Preset",
                "Previous",
                "Cycle back",
                self.controller.previous_preset,
            ),
            (
                "next_preset",
                "→",
                "Preset →",
                "Next",
                "Cycle forward",
                self.controller.next_preset,
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

        all_presets = self.controller.presets
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
            self._bind_click_recursive(tile, lambda p=preset: self.controller.tune_preset(p))

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
        self._status(
            f"{self.panel_config.title} preset bank "
            f"{self.preset_bank_index + 1}/{self._preset_bank_count()}"
        )

    def _preset_bank_count(self) -> int:
        total = len(self.controller.presets)
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

    def render_state(self, state: RadioPanelState) -> None:
        """Render a complete radio-panel state snapshot."""
        empty = self.layout["empty_value"]

        if state.frequency_hz is None:
            self._set_radio_status_value("frequency", empty)
        else:
            self._set_radio_status_value(
                "frequency",
                format_frequency(state.frequency_hz),
            )
            if (
                self.on_frequency_changed is not None
                and state.frequency_hz != self._last_frequency_hz
            ):
                self._last_frequency_hz = state.frequency_hz
                self.on_frequency_changed(state.frequency_hz)

        if state.preset_index is None:
            self._set_radio_status_value("preset", empty)
        else:
            self._set_radio_status_value(
                "preset",
                f"{state.preset_index + 1}/{state.preset_count}",
            )

        self._set_radio_status_value("mode", state.mode_name or empty)
        self._set_radio_status_value(
            "signal",
            self._format_status_value(state.signal_strength),
        )
        self._set_radio_status_value(
            "snr",
            self._format_status_value(state.snr),
        )
        self._set_radio_status_value("rds", state.rds or empty)

        if state.active_preset is not None:
            self._set_active_preset_tile(state.active_preset)
            self._ensure_preset_bank_visible(state.active_preset)
        else:
            self._clear_active_preset_tile()

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

    def _ensure_preset_bank_visible(self, preset: RadioPreset) -> None:
        try:
            preset_index = self.controller.presets.index(preset)
        except ValueError:
            return

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

    def start_radio_status_polling(self, interval_ms: int = RADIO_PANEL_THEME["layout"]["poll_interval_ms"]) -> None:
        """Begin periodic state refreshes at ``interval_ms``."""
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

        self.controller.refresh_state(include_telemetry=True)

        self._status_poll_after_id = self.parent.after(
            interval_ms,
            lambda: self._poll_radio_status(interval_ms),
        )
