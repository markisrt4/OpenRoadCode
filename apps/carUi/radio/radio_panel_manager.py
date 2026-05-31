from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from apps.carUi.radio.radio_panel_config import RadioPanelConfig
from apps.carUi.radio.radio_panel_controller import RadioPanelController
from apps.carUi.radio.radio_status_formatter import (
    compact_preset_label,
    format_frequency,
    format_step,
)
from apps.common.uiTheme import COLORS, FONTS, FONT_FAMILY
from apps.launchers.app_launcher_if import AppLauncherIf
from modules.radio.radio_controller import RadioController
from modules.radio.radio_types import RadioPreset
from modules.sdr.sdr_telemetry_monitor import SDRTelemetryMonitor


class RadioPanelManager:
    def __init__(
        self,
        parent: tk.Widget,
        create_tile: Callable[[tk.Widget, str, str, str, str], tk.Frame],
        radio_controller: RadioController,
        radio_app_launcher: AppLauncherIf,
        panel_config: RadioPanelConfig,
        remote_display: str = ":2",
        set_status: Optional[Callable[[str], None]] = None,
        on_preset_pressed: Optional[Callable[[RadioPreset], None]] = None,
        on_frequency_changed: Optional[Callable[[int], None]] = None,
        presets_per_bank: int = 6,
    ) -> None:
        self.parent = parent
        self.create_tile = create_tile
        self.radio_controller = radio_controller
        self.panel_config = panel_config
        self.on_frequency_changed = on_frequency_changed
        self.compact_ui = bool(
            getattr(parent.winfo_toplevel(), "compact_ui", False)
        )

        self.frame: Optional[tk.Frame] = None

        self.controller = RadioPanelController(
            radio_controller=radio_controller,
            radio_app_launcher=radio_app_launcher,
            panel_config=panel_config,
            remote_display=remote_display,
            set_status=set_status,
            on_preset_pressed=on_preset_pressed,
            update_radio_status=self._update_radio_status,
            on_frequency_tuned=self._handle_frequency_tuned,
        )

        self.set_status = set_status

        self.preset_tiles: dict[int, tk.Frame] = {}
        self.active_preset_frequency_hz: Optional[int] = None

        self.presets_per_bank = max(1, presets_per_bank)
        self.preset_bank_index = 0
        self.preset_grid: Optional[tk.Frame] = None
        self.preset_bank_label_var = tk.StringVar(value="Bank 1/1")

        self.radio_status_widgets: dict[str, tk.Label] = {}
        self.last_preset: Optional[RadioPreset] = None

        self.telemetry_monitor = SDRTelemetryMonitor(radio_controller)
        self._status_poll_after_id: Optional[str] = None

    def show(self) -> tk.Frame:
        self.destroy()

        self.frame = tk.Frame(self.parent, bg=self._app_bg())
        self.frame.pack(fill="both", expand=True)

        self._build_panel(self.frame)
        self._update_radio_status()
        self.start_radio_status_polling()
        self._status(f"{self.panel_config.title} ready")

        return self.frame

    def destroy(self) -> None:
        self.stop_radio_status_polling()

        if self.frame is not None:
            self.frame.destroy()
            self.frame = None

    def _build_panel(self, root: tk.Frame) -> None:
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        root.rowconfigure(1, weight=0)

        main = tk.Frame(root, bg=self._app_bg())
        main.grid(row=0, column=0, sticky="nsew")

        # Keep a stable left/right split on the 800x480 Pi display.
        # Without a uniform group, oversized control labels can force the
        # preset column into useless slivers. Because apparently widgets
        # demand territory now.
        main.columnconfigure(0, weight=3, uniform=f"{self.panel_config.key}_main")
        main.columnconfigure(1, weight=2, uniform=f"{self.panel_config.key}_main")
        main.rowconfigure(0, weight=1)

        control_col = tk.Frame(main, bg=self._app_bg())
        control_col.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        preset_area = tk.Frame(main, bg=self._app_bg())
        preset_area.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        preset_area.columnconfigure(0, weight=1)
        preset_area.rowconfigure(0, weight=1)
        preset_area.rowconfigure(1, weight=0)

        self.preset_grid = tk.Frame(preset_area, bg=self._app_bg())
        self.preset_grid.grid(row=0, column=0, sticky="nsew")

        self._build_control_tiles(control_col)
        self._build_preset_tiles(self.preset_grid)
        self._build_preset_bank_nav(preset_area)
        self._build_status_row(root)

    def _build_control_tiles(self, parent: tk.Frame) -> None:
        parent.columnconfigure(0, weight=1, uniform=f"{self.panel_config.key}_control_col")
        parent.columnconfigure(1, weight=1, uniform=f"{self.panel_config.key}_control_col")

        for row in range(3):
            parent.rowconfigure(row, weight=1, uniform=f"{self.panel_config.key}_control_row")

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
            row = index // 2
            col = index % 2

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

        all_presets = self.radio_controller.presets
        bank_count = self._preset_bank_count()
        self.preset_bank_index = min(self.preset_bank_index, bank_count - 1)

        start = self.preset_bank_index * self.presets_per_bank
        end = start + self.presets_per_bank
        presets = all_presets[start:end]

        cols = max(1, self.panel_config.preset_columns)
        rows = max(1, (len(presets) + cols - 1) // cols)

        for row in range(rows):
            parent.rowconfigure(row, weight=1, uniform=f"{self.panel_config.key}_preset_row")

        for col in range(cols):
            parent.columnconfigure(col, weight=1, uniform=f"{self.panel_config.key}_preset_col")

        precision = 3 if self.panel_config.key in {"airband", "ham", "weather_radio"} else 1

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
            preset_pad = 4 if self.compact_ui else 6
            tile.grid(row=row, column=col, sticky="nsew", padx=preset_pad, pady=preset_pad)
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
            bg=self._tile_bg(),
            highlightthickness=2,
            highlightbackground=self._tile_border(),
            highlightcolor=self._primary_value_fg(),
            bd=0,
            cursor="hand2",
        )
        tile.car_tile_kind = "preset"  # type: ignore[attr-defined]
        tile.car_tile_key = key  # type: ignore[attr-defined]

        tile.columnconfigure(0, weight=1)
        tile.rowconfigure(0, weight=0)
        tile.rowconfigure(1, weight=1)
        tile.rowconfigure(2, weight=0)

        number_label = tk.Label(
            tile,
            text=f"#{number}",
            font=self._preset_number_font(),
            bg=self._tile_bg(),
            fg=self._primary_value_fg(),
            anchor="w",
        )
        number_label.grid(
            row=0,
            column=0,
            sticky="nw",
            padx=8 if self.compact_ui else 10,
            pady=(5 if self.compact_ui else 7, 0),
        )

        freq_label = tk.Label(
            tile,
            text=frequency_text,
            font=self._preset_frequency_font(),
            bg=self._tile_bg(),
            fg=self._tile_fg(),
            anchor="center",
        )
        freq_label.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=6 if self.compact_ui else 8,
            pady=(0, 0),
        )

        detail_label = tk.Label(
            tile,
            text=detail,
            font=self._preset_detail_font(),
            bg=self._tile_bg(),
            fg=self._tile_subtitle_fg(),
            anchor="center",
        )
        detail_label.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=6 if self.compact_ui else 8,
            pady=(0, 5 if self.compact_ui else 9),
        )

        return tile

    def _build_preset_bank_nav(self, parent: tk.Frame) -> None:
        nav = tk.Frame(parent, bg=self._app_bg())
        nav.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        nav.columnconfigure(0, weight=1)
        nav.columnconfigure(1, weight=1)
        nav.columnconfigure(2, weight=1)

        prev_button = tk.Button(
            nav,
            text="◀ Bank",
            font=self._small_button_font(),
            bg=self._button_bg(),
            fg=self._button_fg(),
            activebackground=self._primary_value_fg(),
            activeforeground=self._status_bg(),
            bd=0,
            padx=8,
            pady=3,
            command=self.previous_preset_bank,
            cursor="hand2",
        )
        prev_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        label = tk.Label(
            nav,
            textvariable=self.preset_bank_label_var,
            font=self._small_button_font(),
            bg=self._app_bg(),
            fg=self._primary_value_fg(),
            anchor="center",
            padx=4,
        )
        label.grid(row=0, column=1, sticky="ew")

        next_button = tk.Button(
            nav,
            text="Bank ▶",
            font=self._small_button_font(),
            bg=self._button_bg(),
            fg=self._button_fg(),
            activebackground=self._primary_value_fg(),
            activeforeground=self._status_bg(),
            bd=0,
            padx=8,
            pady=3,
            command=self.next_preset_bank,
            cursor="hand2",
        )
        next_button.grid(row=0, column=2, sticky="ew", padx=(4, 0))

    def previous_preset_bank(self) -> None:
        bank_count = self._preset_bank_count()
        self.preset_bank_index = (self.preset_bank_index - 1) % bank_count
        self._refresh_preset_bank()

    def next_preset_bank(self) -> None:
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
        total = len(self.radio_controller.presets)
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
        control_pad = 4 if self.compact_ui else 6
        tile.grid(row=row, column=col, sticky="nsew", padx=control_pad, pady=control_pad)
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
            bg=self._tile_bg(),
            highlightthickness=2,
            highlightbackground=self._tile_border(),
            highlightcolor=self._primary_value_fg(),
            bd=0,
            cursor="hand2",
        )
        tile.car_tile_kind = "control"  # type: ignore[attr-defined]
        tile.car_tile_key = key  # type: ignore[attr-defined]

        accent = tk.Frame(tile, bg=self._primary_value_fg(), height=4)
        accent.pack(fill="x", side="top")

        body = tk.Frame(tile, bg=self._tile_bg())
        body.pack(
            fill="both",
            expand=True,
            padx=8 if self.compact_ui else 14,
            pady=7 if self.compact_ui else 10,
        )

        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        icon_label = tk.Label(
            body,
            text=icon,
            font=self._control_icon_font(),
            bg=self._tile_bg(),
            fg=self._primary_value_fg(),
            width=1 if self.compact_ui else 2,
            anchor="center",
        )
        icon_label.grid(
            row=0,
            column=0,
            sticky="n",
            padx=(0, 6 if self.compact_ui else 12),
            pady=(1 if self.compact_ui else 2, 0),
        )

        text_area = tk.Frame(body, bg=self._tile_bg())
        text_area.grid(row=0, column=1, sticky="nsew")

        title = tk.Label(
            text_area,
            text=label,
            font=self._control_title_font(),
            bg=self._tile_bg(),
            fg=self._tile_fg(),
            anchor="w",
            justify="left",
            wraplength=120 if self.compact_ui else 260,
        )
        title.pack(fill="x", anchor="w")

        subtitle_label = tk.Label(
            text_area,
            text=subtitle,
            font=self._control_subtitle_font(),
            bg=self._tile_bg(),
            fg=self._tile_subtitle_fg(),
            anchor="w",
            justify="left",
            wraplength=120 if self.compact_ui else 260,
        )
        subtitle_label.pack(fill="x", anchor="w", pady=(4 if self.compact_ui else 7, 0))

        detail_label = tk.Label(
            text_area,
            text=detail,
            font=self._control_detail_font(),
            bg=self._tile_bg(),
            fg=self._tile_detail_fg(),
            anchor="w",
            justify="left",
            wraplength=120 if self.compact_ui else 260,
        )
        detail_label.pack(fill="x", anchor="w", pady=(2 if self.compact_ui else 3, 0))

        return tile

    def _build_status_row(self, parent: tk.Frame) -> None:
        status = tk.Frame(parent, bg=self._status_bg())
        status.grid(row=1, column=0, sticky="ew", pady=(6, 0), ipady=3)

        for col in range(6):
            status.columnconfigure(col, weight=1)

        fields = [
            ("frequency", "Freq:", "--", self._primary_value_fg()),
            ("preset", "Preset:", "--", self._primary_value_fg()),
            ("mode", "Mode:", "--", self._primary_value_fg()),
            ("signal", "Signal:", "--", self._telemetry_value_fg()),
            ("snr", "SNR:", "--", self._telemetry_value_fg()),
            ("rds", "RDS:", "--", self._telemetry_value_fg()),
        ]

        for col, (key, label_text, value_text, value_fg) in enumerate(fields):
            group = tk.Frame(status, bg=self._status_bg())
            group.grid(row=0, column=col, sticky="nsew", padx=4)

            label = tk.Label(
                group,
                text=label_text,
                bg=self._status_bg(),
                fg=self._status_label_fg(),
                font=self._status_font(),
            )
            label.pack(side="left")

            value = tk.Label(
                group,
                text=value_text,
                bg=self._status_bg(),
                fg=value_fg,
                font=self._status_font(),
            )
            value.pack(side="left", padx=(4, 0))

            self.radio_status_widgets[key] = value

    def _update_radio_status(
        self,
        frequency_hz: Optional[int] = None,
        preset: Optional[RadioPreset] = None,
    ) -> None:
        if frequency_hz is None:
            frequency_hz = getattr(self.radio_controller, "current_frequency_hz", None)

        if preset is not None:
            self.last_preset = preset

        active_preset = preset or self.last_preset

        if frequency_hz is not None:
            self._set_radio_status_value("frequency", format_frequency(frequency_hz))
            if self.on_frequency_changed:
                self.on_frequency_changed(frequency_hz)
        else:
            self._set_radio_status_value("frequency", "--")

        if active_preset is not None:
            try:
                index = self.radio_controller.presets.index(active_preset) + 1
                count = len(self.radio_controller.presets)
                self._set_radio_status_value("preset", f"{index}/{count}")
            except ValueError:
                self._set_radio_status_value("preset", "--")
        else:
            self._set_radio_status_value("preset", "--")

        self._set_radio_status_value("mode", self._current_mode_name())

    def _bind_click_recursive(self, widget: tk.Widget, callback: Callable[[], None]) -> None:
        widget.bind("<Button-1>", lambda event: callback())

        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback)

    def _status(self, message: str) -> None:
        if self.set_status:
            self.set_status(message)

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

        bg = self._active_preset_bg() if active else self._tile_bg()
        border = self._primary_value_fg() if active else self._tile_border()
        freq_fg = self._status_bg() if active else self._tile_fg()
        detail_fg = self._status_bg() if active else self._tile_subtitle_fg()

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
                    child.configure(bg=bg, fg=self._primary_value_fg())
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

    def _handle_frequency_tuned(
        self,
        frequency_hz: int,
        preset: Optional[RadioPreset] = None,
    ) -> None:
        matched_preset = preset or self._find_preset_by_frequency(frequency_hz)

        if matched_preset is not None:
            self.last_preset = matched_preset
            self._set_active_preset_tile(matched_preset)
            self._ensure_preset_bank_visible(matched_preset)
        else:
            self._clear_active_preset_tile()

        self._update_radio_status(frequency_hz=frequency_hz, preset=matched_preset)

    def _ensure_preset_bank_visible(self, preset: RadioPreset) -> None:
        try:
            preset_index = self.radio_controller.presets.index(preset)
        except ValueError:
            return

        wanted_bank_index = preset_index // self.presets_per_bank
        if wanted_bank_index == self.preset_bank_index:
            return

        self.preset_bank_index = wanted_bank_index
        self._refresh_preset_bank()

    def _find_preset_by_frequency(self, frequency_hz: int) -> Optional[RadioPreset]:
        for preset in self.radio_controller.presets:
            if preset.frequency_hz == frequency_hz:
                return preset
        return None

    def _clear_active_preset_tile(self) -> None:
        self.active_preset_frequency_hz = None

        for tile in self.preset_tiles.values():
            self._set_tile_active(tile, False)

    def _set_radio_status_value(self, key: str, value: str) -> None:
        widget = self.radio_status_widgets.get(key)
        if widget is not None:
            widget.config(text=value)

    def start_radio_status_polling(self, interval_ms: int = 2000) -> None:
        self.stop_radio_status_polling()
        self._poll_radio_status(interval_ms)

    def stop_radio_status_polling(self) -> None:
        if self._status_poll_after_id is None:
            return

        try:
            self.parent.after_cancel(self._status_poll_after_id)
        except Exception:
            pass

        self._status_poll_after_id = None

    def _poll_radio_status(self, interval_ms: int) -> None:
        if self.frame is None:
            return

        mode_name = self._current_mode_name()
        telemetry = self.telemetry_monitor.read(include_rds=(mode_name == "WFM"))

        self._update_radio_status(
            frequency_hz=telemetry.frequency_hz,
            preset=self.last_preset,
        )

        self._set_radio_status_value("signal", telemetry.signal)
        self._set_radio_status_value("snr", telemetry.snr)
        self._set_radio_status_value("rds", telemetry.rds)

        self._status_poll_after_id = self.parent.after(
            interval_ms,
            lambda: self._poll_radio_status(interval_ms),
        )

    def _current_mode_name(self) -> str:
        if self.last_preset is not None:
            return self.last_preset.mode.name

        mode = getattr(self.radio_controller, "default_mode", None)
        return getattr(mode, "name", "--")

    @staticmethod
    def _app_bg() -> str:
        return COLORS.get("app_bg", "#111418")

    @staticmethod
    def _status_bg() -> str:
        return COLORS.get("status_bg", "#0b0d10")

    @staticmethod
    def _status_fg() -> str:
        return COLORS.get("status_fg", "#d8dee9")

    @staticmethod
    def _status_font():
        return FONTS.get("status", (FONT_FAMILY, 10))

    @staticmethod
    def _tile_bg() -> str:
        return COLORS.get("tile_bg", "#20252b")

    @staticmethod
    def _tile_border() -> str:
        return COLORS.get("tile_border", "#384653")

    @staticmethod
    def _tile_fg() -> str:
        return COLORS.get("tile_title", "#ffffff")

    @staticmethod
    def _tile_subtitle_fg() -> str:
        return COLORS.get("tile_subtitle", "#b8c7d3")

    @staticmethod
    def _tile_detail_fg() -> str:
        return COLORS.get("tile_detail", "#7f8d99")

    @staticmethod
    def _button_bg() -> str:
        return COLORS.get("tile_bg", "#20252b")

    @staticmethod
    def _button_fg() -> str:
        return COLORS.get("tile_title", "#ffffff")

    def _small_button_font(self):
        if self.compact_ui:
            return (FONT_FAMILY, 8)
        return FONTS.get("status", (FONT_FAMILY, 10))

    def _control_icon_font(self):
        if self.compact_ui:
            return (FONT_FAMILY, 20, "bold")
        return (FONT_FAMILY, 28, "bold")

    def _control_title_font(self):
        if self.compact_ui:
            return (FONT_FAMILY, 18, "bold")
        return FONTS.get("tile_title", (FONT_FAMILY, 24, "bold"))

    def _control_subtitle_font(self):
        if self.compact_ui:
            return (FONT_FAMILY, 10)
        return FONTS.get("tile_subtitle", (FONT_FAMILY, 14))

    def _control_detail_font(self):
        if self.compact_ui:
            return (FONT_FAMILY, 8)
        return FONTS.get("tile_detail", (FONT_FAMILY, 11))

    def _preset_number_font(self):
        if self.compact_ui:
            return (FONT_FAMILY, 10, "bold")
        return (FONT_FAMILY, 13, "bold")

    def _preset_frequency_font(self):
        if self.compact_ui:
            return (FONT_FAMILY, 17, "bold")
        return (FONT_FAMILY, 24, "bold")

    def _preset_detail_font(self):
        if self.compact_ui:
            return (FONT_FAMILY, 8)
        return FONTS.get("tile_subtitle", (FONT_FAMILY, 13))

    @staticmethod
    def _primary_value_fg() -> str:
        return COLORS.get("status_primary_value", "#1f7cff")

    @staticmethod
    def _telemetry_value_fg() -> str:
        return COLORS.get("status_telemetry_value", "#48d11f")

    @staticmethod
    def _status_label_fg() -> str:
        return COLORS.get("status_label", "#9aa4b2")

    @staticmethod
    def _active_preset_bg() -> str:
        return COLORS.get("preset_active_bg", "#d8e0eb")
