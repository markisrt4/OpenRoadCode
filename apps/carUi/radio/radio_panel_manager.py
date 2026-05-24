from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from apps.carUi.radio.radio_panel_config import (
    RadioPanelConfig,
)

from apps.carUi.radio.radio_panel_controller import (
    RadioPanelController,
)

from apps.carUi.radio.radio_status_formatter import (
    compact_preset_label,
    format_frequency,
    format_step,
)

from apps.launchers.app_launcher_if import AppLauncherIf

from modules.radio.radio_controller import RadioController
from modules.radio.radio_types import RadioPreset


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
    ) -> None:
        self.parent = parent
        self.create_tile = create_tile
        self.radio_controller = radio_controller
        self.panel_config = panel_config
        self.on_frequency_changed = on_frequency_changed

        self.frame: Optional[tk.Frame] = None
        self.radio_status_var = tk.StringVar(value="Radio status: --")

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

    def show(self) -> tk.Frame:
        self.destroy()

        self.frame = tk.Frame(self.parent, bg=self._app_bg())
        self.frame.pack(fill="both", expand=True)

        self._build_panel(self.frame)
        self._update_radio_status()
        self._status(f"{self.panel_config.title} ready")

        return self.frame

    def destroy(self) -> None:
        if self.frame is not None:
            self.frame.destroy()
            self.frame = None

    def _build_panel(self, root: tk.Frame) -> None:
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        root.rowconfigure(1, weight=0)

        main = tk.Frame(root, bg=self._app_bg())
        main.grid(row=0, column=0, sticky="nsew")

        main.columnconfigure(0, weight=2)
        main.columnconfigure(1, weight=3)
        main.rowconfigure(0, weight=1)

        control_col = tk.Frame(main, bg=self._app_bg())
        control_col.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        preset_grid = tk.Frame(main, bg=self._app_bg())
        preset_grid.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self._build_control_tiles(control_col)
        self._build_preset_tiles(preset_grid)
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
                self.panel_config.launch_tile.label,
                self.panel_config.launch_tile.subtitle,
                self.panel_config.launch_tile.detail,
                self.controller.toggle_radio_app,
            ),
            (
                "toggle_radio",
                self.panel_config.radio_toggle_tile.label,
                self.panel_config.radio_toggle_tile.subtitle,
                self.panel_config.radio_toggle_tile.detail,
                self.controller.toggle_radio,
            ),
            (
                "freq_down",
                "Tune −",
                "Down",
                f"Step: {step_label}",
                self.controller.frequency_down,
            ),
            (
                "freq_up",
                "Tune +",
                "Up",
                f"Step: {step_label}",
                self.controller.frequency_up,
            ),
            (
                "previous_preset",
                "Preset ←",
                "Previous",
                "Cycle back",
                self.controller.previous_preset,
            ),
            (
                "next_preset",
                "Preset →",
                "Next",
                "Cycle forward",
                self.controller.next_preset,
            ),
        ]

        for index, (key, label, subtitle, detail, callback) in enumerate(controls):
            row = index // 2
            col = index % 2

            self._add_control_tile(
                parent=parent,
                row=row,
                col=col,
                key=key,
                label=label,
                subtitle=subtitle,
                detail=detail,
                callback=callback,
            )

    def _build_preset_tiles(self, parent: tk.Frame) -> None:
        presets = self.radio_controller.presets
        cols = max(1, self.panel_config.preset_columns)
        rows = max(1, (len(presets) + cols - 1) // cols)

        for row in range(rows):
            parent.rowconfigure(row, weight=1, uniform=f"{self.panel_config.key}_preset_row")

        for col in range(cols):
            parent.columnconfigure(col, weight=1, uniform=f"{self.panel_config.key}_preset_col")

        for index, preset in enumerate(presets):
            row = index // cols
            col = index % cols

            preset_number = index + 1

            precision = (3
                if self.panel_config.key in {
                    "airband",
                    "ham",
                    "weather_radio",
                }
                else 1
            )
            tile = self.create_tile(
                parent,
                f"{self.panel_config.key}_preset_{preset.frequency_hz}",
                compact_preset_label(preset, precision=precision),
                f"Preset {preset_number}",
                format_frequency(
                    preset.frequency_hz,
                    precision=3 if self.panel_config.key in {
                        "airband",
                        "ham",
                        "weather_radio",
                    } else 1,
                ),
            )
            self.preset_tiles[preset.frequency_hz] = tile
            tile.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
            self._bind_click_recursive(tile, lambda p=preset: self.controller.tune_preset(p))

    def _add_control_tile(
        self,
        parent: tk.Frame,
        row: int,
        col: int,
        key: str,
        label: str,
        subtitle: str,
        detail: str,
        callback: Callable[[], None],
    ) -> None:
        tile = self.create_tile(
            parent,
            f"{self.panel_config.key}_{key}",
            label,
            subtitle,
            detail,
        )
        tile.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
        self._bind_click_recursive(tile, callback)

    def _build_status_row(self, parent: tk.Frame) -> None:
        status = tk.Label(
            parent,
            textvariable=self.radio_status_var,
            anchor="w",
            bg=self._status_bg(),
            fg=self._status_fg(),
            font=self._status_font(),
            padx=10,
            pady=3,
        )
        status.grid(row=1, column=0, sticky="ew", pady=(6, 0))

    def _update_radio_status(
        self,
        frequency_hz: Optional[int] = None,
        preset: Optional[RadioPreset] = None,
    ) -> None:
        if frequency_hz is None:
            frequency_hz = getattr(self.radio_controller, "current_frequency_hz", None)

        parts = []

        if frequency_hz is not None:
            parts.append(f"Freq: {format_frequency(frequency_hz)}")
            if self.on_frequency_changed:
                self.on_frequency_changed(frequency_hz)

        if preset is not None:
            try:
                index = self.radio_controller.presets.index(preset) + 1
                count = len(self.radio_controller.presets)
                parts.append(f"Preset: {index}/{count} {preset.label}")
            except ValueError:
                parts.append(f"Preset: {preset.label}")
        else:
            parts.append("Preset: --")

        mode_name = None
        if preset is not None:
            mode_name = preset.mode.name
        elif hasattr(self.radio_controller, "default_mode"):
            mode_name = self.radio_controller.default_mode.name

        parts.append(f"Mode: {mode_name or '--'}")
        parts.append("Signal: --")
        parts.append("SNR: --")
        parts.append("RDS: --")

        self.radio_status_var.set("   |   ".join(parts))

    def _bind_click_recursive(self, widget: tk.Widget, callback: Callable[[], None]) -> None:
        widget.bind("<Button-1>", lambda event: callback())

        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback)

    def _status(self, message: str) -> None:
        if self.set_status:
            self.set_status(message)

    def _set_active_preset_tile(self, preset: RadioPreset) -> None:
        self.active_preset_frequency_hz = preset.frequency_hz

        for frequency_hz, tile in self.preset_tiles.items():
            active = frequency_hz == preset.frequency_hz
            self._set_tile_active(tile, active)


    def _set_tile_active(self, tile: tk.Widget, active: bool) -> None:
        bg = self._status_fg() if active else self._tile_bg()
        fg = self._status_bg() if active else self._tile_fg()

        self._apply_widget_colors(tile, bg=bg, fg=fg)


    def _apply_widget_colors(self, widget: tk.Widget, bg: str, fg: str) -> None:
        try:
            widget.configure(bg=bg)
        except tk.TclError:
            pass

        if isinstance(widget, tk.Label):
            try:
                widget.configure(bg=bg, fg=fg)
            except tk.TclError:
                pass

        for child in widget.winfo_children():
            self._apply_widget_colors(child, bg, fg)

    def _handle_frequency_tuned(
        self,
        frequency_hz: int,
        preset: Optional[RadioPreset] = None,
    ) -> None:
        matched_preset = preset or self._find_preset_by_frequency(frequency_hz)

        if matched_preset is not None:
            self._set_active_preset_tile(matched_preset)
        else:
            self._clear_active_preset_tile()


    def _find_preset_by_frequency(self, frequency_hz: int) -> Optional[RadioPreset]:
        for preset in self.radio_controller.presets:
            if preset.frequency_hz == frequency_hz:
                return preset
        return None


    def _clear_active_preset_tile(self) -> None:
        self.active_preset_frequency_hz = None

        for tile in self.preset_tiles.values():
            self._set_tile_active(tile, False)

    @staticmethod
    def _app_bg() -> str:
        try:
            from apps.carUi.uiTheme import COLORS
            return COLORS["app_bg"]
        except Exception:
            return "#111418"

    @staticmethod
    def _status_bg() -> str:
        try:
            from apps.carUi.uiTheme import COLORS
            return COLORS["status_bg"]
        except Exception:
            return "#1b1f26"

    @staticmethod
    def _status_fg() -> str:
        try:
            from apps.carUi.uiTheme import COLORS
            return COLORS["status_fg"]
        except Exception:
            return "#d8dee9"

    @staticmethod
    def _status_font():
        try:
            from apps.carUi.uiTheme import FONTS
            return FONTS["status"]
        except Exception:
            return ("Arial", 10)
        
    @staticmethod
    def _tile_bg() -> str:
        try:
            from apps.carUi.uiTheme import COLORS
            return COLORS["tile_bg"]
        except Exception:
            return "#20252b"


    @staticmethod
    def _tile_fg() -> str:
        try:
            from apps.carUi.uiTheme import COLORS
            return COLORS["tile_title"]
        except Exception:
            return "#ffffff"
