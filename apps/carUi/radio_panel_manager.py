from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Optional

from apps.launchers.app_launcher_if import AppLauncherIf
from modules.radio.radio_controller import RadioController
from modules.radio.radio_types import RadioPreset


@dataclass(frozen=True)
class RadioStatusSnapshot:
    frequency_hz: Optional[int] = None
    mode: Optional[str] = None
    preset_label: Optional[str] = None
    preset_index: Optional[int] = None
    preset_count: Optional[int] = None
    signal_strength: Optional[str] = None
    snr: Optional[str] = None
    rds: Optional[str] = None

@dataclass(frozen=True)
class RadioPanelTileConfig:
    label: str
    subtitle: str
    detail: str


@dataclass(frozen=True)
class RadioPanelConfig:
    key: str
    title: str
    launch_tile: RadioPanelTileConfig
    radio_toggle_tile: RadioPanelTileConfig
    default_step_hz: int
    default_mode_name: str = "Radio"
    preset_columns: int = 2


class RadioPanelManager:
    """
    Tkinter radio subpanel manager.

    Responsibilities:
      - Build and own the reusable radio-control subpanel UI.
      - Render common radio actions:
          - launch/toggle external radio app
          - radio on/off
          - tune up/down
          - presets
      - Delegate radio behavior to RadioController.
      - Delegate external application launch/toggle to RadioAppLauncherIf.

    Non-responsibilities:
      - No RigCTL knowledge.
      - No SDR++ process implementation details.
      - No radio backend details.
      - No keyboard/rotary adapter ownership.
    """

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
        self.radio_app_launcher = radio_app_launcher
        self.panel_config = panel_config
        self.remote_display = remote_display
        self.set_status = set_status
        self.on_preset_pressed = on_preset_pressed
        self.on_frequency_changed = on_frequency_changed

        self.frame: Optional[tk.Frame] = None
        self.radio_running = False

        self.radio_status_var = tk.StringVar(value="Radio status: --")

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

    def toggle_radio_app(self) -> None:
        try:
            running = self.radio_app_launcher.toggle(
                remote_display=self.remote_display,
                set_status=self.set_status,
            )

            if running:
                self._status(f"{self.panel_config.title} app launched")

                # Give SDR++ / rigctl a moment to come up before tuning.
                self.parent.after(1500, self._start_radio_after_app_launch)
            else:
                self.radio_running = False
                self._status(f"{self.panel_config.title} app stopped")

        except Exception as exc:
            self._status(f"{self.panel_config.title} app toggle failed: {exc}")
            print(f"[{self.panel_config.key}] app toggle failed: {exc}")

    def toggle_radio(self) -> None:
        try:
            if self.radio_running:
                self.radio_controller.stop()
                self.radio_running = False
                self._status(f"{self.panel_config.title} radio stopped")
                return

            self.radio_controller.start()
            self.radio_running = True

            frequency = getattr(self.radio_controller, "current_frequency_hz", None)

            self._update_radio_status(frequency_hz=frequency)
            self._status(f"{self.panel_config.title} radio started")

        except OSError as exc:
            self.radio_running = False
            self._status(f"{self.panel_config.title} radio unavailable: {exc}")
            print(f"[{self.panel_config.key}] radio unavailable: {exc}")

        except Exception as exc:
            self.radio_running = False
            self._status(f"{self.panel_config.title} radio start failed: {exc}")
            print(f"[{self.panel_config.key}] radio start failed: {exc}")
            
    def tune_preset(self, preset: RadioPreset) -> None:
        try:
            self.radio_controller.tune_preset(preset)
            self._status(
                f"{self.panel_config.title}: {preset.label} "
                f"({self._format_frequency(preset.frequency_hz)})"
            )

            if self.on_preset_pressed:
                self.on_preset_pressed(preset)

            self._update_radio_status(
                frequency_hz=preset.frequency_hz,
                preset=preset,
            )

        except OSError as exc:
            self._status(f"{self.panel_config.title} preset failed: {exc}")
            print(f"[{self.panel_config.key}] preset failed: {exc}")

    def frequency_up(self) -> None:
        try:
            frequency = self.radio_controller.frequency_up()
            self._status(f"{self.panel_config.title}: {self._format_frequency(frequency)}")
            self._update_radio_status(frequency_hz=frequency)

        except OSError as exc:
            self._status(f"{self.panel_config.title} tune up failed: {exc}")
            print(f"[{self.panel_config.key}] tune up failed: {exc}")

    def frequency_down(self) -> None:
        try:
            frequency = self.radio_controller.frequency_down()
            self._status(f"{self.panel_config.title}: {self._format_frequency(frequency)}")
            self._update_radio_status(frequency_hz=frequency)

        except OSError as exc:
            self._status(f"{self.panel_config.title} tune down failed: {exc}")
            print(f"[{self.panel_config.key}] tune down failed: {exc}")

    def next_preset(self) -> None:
        try:
            preset = self.radio_controller.next_preset()
            self._status(f"{self.panel_config.title}: {preset.label}")
            self._update_radio_status(
                frequency_hz=preset.frequency_hz,
                preset=preset,
            )

        except (OSError, ValueError) as exc:
            self._status(f"{self.panel_config.title} next preset failed: {exc}")
            print(f"[{self.panel_config.key}] next preset failed: {exc}")

    def previous_preset(self) -> None:
        try:
            preset = self.radio_controller.previous_preset()
            self._status(f"{self.panel_config.title}: {preset.label}")
            self._update_radio_status(
                frequency_hz=preset.frequency_hz,
                preset=preset,
            )

        except (OSError, ValueError) as exc:
            self._status(f"{self.panel_config.title} previous preset failed: {exc}")
            print(f"[{self.panel_config.key}] previous preset failed: {exc}")

    def _build_panel(self, root: tk.Frame) -> None:
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(0, weight=1)
        root.rowconfigure(1, weight=0)

        main = tk.Frame(root, bg=self._app_bg())
        main.grid(row=0, column=0, columnspan=2, sticky="nsew")

        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        control_col = tk.Frame(main, bg=self._app_bg())
        control_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        preset_grid = tk.Frame(main, bg=self._app_bg())
        preset_grid.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self._build_control_tiles(control_col)
        self._build_preset_tiles(preset_grid)
        self._build_status_row(root)

    def _build_status_row(self, parent: tk.Frame) -> None:
        status = tk.Label(
            parent,
            textvariable=self.radio_status_var,
            anchor="w",
            bg=self._status_bg(),
            fg=self._status_fg(),
            font=self._status_font(),
            padx=14,
            pady=8,
        )
        status.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))

    def _update_radio_status(
        self,
        frequency_hz: int | None = None,
        preset: RadioPreset | None = None,
    ) -> None:
        if frequency_hz is None:
            frequency_hz = getattr(self.radio_controller, "current_frequency_hz", None)

        parts = []

        if frequency_hz is not None:
            parts.append(f"Freq: {self._format_frequency(frequency_hz)}")

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

    def _build_control_tiles(self, parent: tk.Frame) -> None:
        for row in range(6):
            parent.rowconfigure(row, weight=1, uniform=f"{self.panel_config.key}_control_row")
        parent.columnconfigure(0, weight=1)

        self._add_control_tile(
            parent,
            row=0,
            key="toggle_app",
            label=self.panel_config.launch_tile.label,
            subtitle=self.panel_config.launch_tile.subtitle,
            detail=self.panel_config.launch_tile.detail,
            callback=self.toggle_radio_app,
        )

        self._add_control_tile(
            parent,
            row=1,
            key="toggle_radio",
            label=self.panel_config.radio_toggle_tile.label,
            subtitle=self.panel_config.radio_toggle_tile.subtitle,
            detail=self.panel_config.radio_toggle_tile.detail,
            callback=self.toggle_radio,
        )

        step_label = self._format_step(self.panel_config.default_step_hz)

        self._add_control_tile(
            parent,
            row=2,
            key="freq_down",
            label="Tune −",
            subtitle="Frequency down",
            detail=f"{self.panel_config.default_mode_name} step: {step_label}",
            callback=self.frequency_down,
        )

        self._add_control_tile(
            parent,
            row=3,
            key="freq_up",
            label="Tune +",
            subtitle="Frequency up",
            detail=f"{self.panel_config.default_mode_name} step: {step_label}",
            callback=self.frequency_up,
        )

        self._add_control_tile(
            parent,
            row=4,
            key="previous_preset",
            label="Preset ←",
            subtitle="Previous preset",
            detail="Cycle backward",
            callback=self.previous_preset,
        )

        self._add_control_tile(
            parent,
            row=5,
            key="next_preset",
            label="Preset →",
            subtitle="Next preset",
            detail="Cycle forward",
            callback=self.next_preset,
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

            tile = self.create_tile(
                parent,
                f"{self.panel_config.key}_preset_{preset.frequency_hz}",
                preset.label,
                preset.mode.name,
                self._format_frequency(preset.frequency_hz),
            )
            tile.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)
            self._bind_click_recursive(tile, lambda p=preset: self.tune_preset(p))

    def _add_control_tile(
        self,
        parent: tk.Frame,
        row: int,
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
        tile.grid(row=row, column=0, sticky="nsew", padx=10, pady=10)
        self._bind_click_recursive(tile, callback)

    def _bind_click_recursive(self, widget: tk.Widget, callback: Callable[[], None]) -> None:
        widget.bind("<Button-1>", lambda event: callback())
        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback)

    def _status(self, message: str) -> None:
        if self.set_status:
            self.set_status(message)

    @staticmethod
    def _format_frequency(frequency_hz: int) -> str:
        if frequency_hz >= 1_000_000:
            value = f"{frequency_hz / 1_000_000:.3f}".rstrip("0").rstrip(".")
            return f"{value} MHz"

        if frequency_hz >= 1_000:
            value = f"{frequency_hz / 1_000:.3f}".rstrip("0").rstrip(".")
            return f"{value} kHz"

        return f"{frequency_hz} Hz"

    @staticmethod
    def _format_step(step_hz: int) -> str:
        if step_hz >= 1_000_000:
            return f"{step_hz / 1_000_000:g} MHz"

        if step_hz >= 1_000:
            return f"{step_hz / 1_000:g} kHz"

        return f"{step_hz:g} Hz"

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
            return ("Arial", 12)
        
    def _start_radio_after_app_launch(self) -> None:
        try:
            self.radio_controller.start()
            self.radio_running = True

            frequency = getattr(self.radio_controller, "current_frequency_hz", None)

            self._update_radio_status(frequency_hz=frequency)
            self._status(f"{self.panel_config.title} tuned and ready")

        except OSError as exc:
            self.radio_running = False
            self._status(f"{self.panel_config.title} rigctl not ready: {exc}")
            print(f"[{self.panel_config.key}] rigctl not ready after app launch: {exc}")

        except Exception as exc:
            self.radio_running = False
            self._status(f"{self.panel_config.title} startup tune failed: {exc}")
            print(f"[{self.panel_config.key}] startup tune failed: {exc}")