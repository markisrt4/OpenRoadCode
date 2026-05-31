import tkinter as tk
from dataclasses import dataclass
from typing import Callable, List, Optional, Protocol

from apps.common.uiTheme import COLORS



class RadioModeLike(Protocol):
    name: str
    bandwidth: int
    step_hz: int


class RadioControllerLike(Protocol):
    def start(self): ...
    def stop(self): ...
    def set_frequency(self, frequency_hz: int): ...
    def get_frequency(self) -> int: ...
    def set_mode(self, mode: RadioModeLike): ...
    def next_station(self): ...
    def previous_station(self): ...
    def frequency_up(self, delta_hz: int | None = None): ...
    def frequency_down(self, delta_hz: int | None = None): ...


@dataclass(frozen=True)
class FMRadioMode:
    name: str = "WFM"
    bandwidth: int = 180_000
    step_hz: int = 100_000


@dataclass(frozen=True)
class FMPreset:
    label: str
    frequency_mhz: float
    mode: FMRadioMode = FMRadioMode()

    @property
    def frequency_hz(self) -> int:
        return int(self.frequency_mhz * 1_000_000)


FM_WIDE = FMRadioMode("WFM", 180_000, 100_000)

DEFAULT_FM_PRESETS: List[FMPreset] = [
    FMPreset("88.7 FM", 88.7, FM_WIDE),
    FMPreset("89.3 FM", 89.3, FM_WIDE),
    FMPreset("93.9 FM", 93.9, FM_WIDE),
    FMPreset("97.1 FM", 97.1, FM_WIDE),
    FMPreset("100.3 FM", 100.3, FM_WIDE),
    FMPreset("101.1 FM", 101.1, FM_WIDE),
    FMPreset("104.3 FM", 104.3, FM_WIDE),
    FMPreset("106.7 FM", 106.7, FM_WIDE),
]


class FMRadioPanel(tk.Frame):
    """
    FM radio subpanel.

    Responsibilities:
      - Render FM controls and presets.
      - Call RadioController methods for radio behavior.
      - Call on_launch_sdrpp callback to launch/toggle the SDR++ app.

    Non-responsibilities:
      - No RigCTL knowledge.
      - No keyboard/encoder adapter ownership.
      - No socket/backend details.
    """

    def __init__(
        self,
        parent: tk.Widget,
        create_tile: Callable[[tk.Widget, str, str, str, str], tk.Frame],
        radio_controller: Optional[RadioControllerLike] = None,
        on_launch_sdrpp: Optional[Callable[[], None]] = None,
        on_preset_pressed: Optional[Callable[[FMPreset], None]] = None,
        presets: Optional[List[FMPreset]] = None,
    ) -> None:
        super().__init__(parent, bg=COLORS["app_bg"], takefocus=True)

        self.create_tile = create_tile
        self.radio_controller = radio_controller
        self.on_launch_sdrpp = on_launch_sdrpp
        self.on_preset_pressed = on_preset_pressed
        self.presets = presets or DEFAULT_FM_PRESETS

        self.current_preset: Optional[FMPreset] = None
        self.radio_running = False

        self._build_ui()

    def _build_ui(self) -> None:
        container = tk.Frame(self, bg=COLORS["app_bg"])
        container.pack(fill="both", expand=True)

        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=2)
        container.rowconfigure(0, weight=1)

        control_col = tk.Frame(container, bg=COLORS["app_bg"])
        control_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        preset_grid = tk.Frame(container, bg=COLORS["app_bg"])
        preset_grid.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        for row in range(4):
            control_col.rowconfigure(row, weight=1, uniform="fm_control_row")
        control_col.columnconfigure(0, weight=1)

        launch_tile = self.create_tile(
            control_col,
            "fm_launch_sdrpp",
            "Launch SDR++",
            "FM receiver app",
            "Starts / toggles SDR++",
        )
        launch_tile.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self._bind_click_recursive(launch_tile, self.launch_sdrpp)

        radio_toggle_tile = self.create_tile(
            control_col,
            "fm_radio_toggle",
            "Radio ON/OFF",
            "Radio control",
            "Start / stop receiver",
        )
        radio_toggle_tile.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self._bind_click_recursive(radio_toggle_tile, self.toggle_radio)

        freq_down_tile = self.create_tile(
            control_col,
            "fm_freq_down",
            "Tune −",
            "Frequency down",
            "WFM step: 100 kHz",
        )
        freq_down_tile.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self._bind_click_recursive(freq_down_tile, self.frequency_down)

        freq_up_tile = self.create_tile(
            control_col,
            "fm_freq_up",
            "Tune +",
            "Frequency up",
            "WFM step: 100 kHz",
        )
        freq_up_tile.grid(row=3, column=0, sticky="nsew", padx=10, pady=10)
        self._bind_click_recursive(freq_up_tile, self.frequency_up)

        cols = 2
        rows = max(1, (len(self.presets) + cols - 1) // cols)

        for row in range(rows):
            preset_grid.rowconfigure(row, weight=1, uniform="fm_row")
        for col in range(cols):
            preset_grid.columnconfigure(col, weight=1, uniform="fm_col")

        for index, preset in enumerate(self.presets):
            row = index // cols
            col = index % cols

            tile = self.create_tile(
                preset_grid,
                f"fm_{preset.frequency_mhz}",
                preset.label,
                preset.mode.name,
                f"{preset.frequency_mhz:.1f} MHz",
            )
            tile.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)
            self._bind_click_recursive(tile, lambda p=preset: self.tune_preset(p))

    def launch_sdrpp(self) -> None:
        if self.on_launch_sdrpp is not None:
            self.on_launch_sdrpp()

    def toggle_radio(self) -> None:
        if self.radio_controller is None:
            return

        try:
            if self.radio_running:
                self.radio_controller.stop()
                self.radio_running = False
            else:
                self.radio_controller.start()
                self.radio_running = True
        except OSError as exc:
            print(f"[FM] Radio controller unavailable: {exc}")

    def tune_preset(self, preset: FMPreset) -> None:
        self.current_preset = preset

        if self.radio_controller is not None:
            try:
                self.radio_controller.set_mode(preset.mode)
                self.radio_controller.set_frequency(preset.frequency_hz)
            except OSError as exc:
                print(f"[FM] Cannot tune preset. Radio controller unavailable: {exc}")

        if self.on_preset_pressed is not None:
            self.on_preset_pressed(preset)

    def frequency_up(self, delta_hz: int | None = None) -> None:
        if self.radio_controller is None:
            return

        delta = delta_hz if delta_hz is not None else self._current_step_hz()

        try:
            self.radio_controller.frequency_up(delta)
        except OSError as exc:
            print(f"[FM] Cannot tune up. Radio controller unavailable: {exc}")

    def frequency_down(self, delta_hz: int | None = None) -> None:
        if self.radio_controller is None:
            return

        delta = delta_hz if delta_hz is not None else self._current_step_hz()

        try:
            self.radio_controller.frequency_down(delta)
        except OSError as exc:
            print(f"[FM] Cannot tune down. Radio controller unavailable: {exc}")

    def set_radio_controller(self, radio_controller: Optional[RadioControllerLike]) -> None:
        self.radio_controller = radio_controller

    def _current_step_hz(self) -> int:
        if self.current_preset is not None:
            return self.current_preset.mode.step_hz
        return FM_WIDE.step_hz

    def _bind_click_recursive(self, widget: tk.Widget, callback: Callable[[], None]) -> None:
        widget.bind("<Button-1>", lambda event: callback())
        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback)
