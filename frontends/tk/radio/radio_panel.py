# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable passive Tk radio panel implementing the semantic radio UI contract."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from frontends.tk.radio.radio_panel_config import RadioPanelConfig
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
    """Present radio state and forward semantic user requests to injected handlers."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        panel_config: RadioPanelConfig,
        theme: dict,
        on_frequency_changed: Callable[[int], None] | None = None,
        presets_per_bank: int = 6,
    ) -> None:
        colors = theme["colors"]
        super().__init__(parent, bg=colors["panel_bg"])
        self._config = panel_config
        self._theme = theme
        self._on_frequency_changed = on_frequency_changed
        self._presets_per_bank = max(1, presets_per_bank)

        self._preset_handler: PresetRequestHandlerIf | None = None
        self._playback_handler: PlaybackRequestHandlerIf | None = None
        self._station_handler: StationRequestHandlerIf | None = None
        self._tuning_handler: TuningRequestHandlerIf | None = None
        self._application_handler: RadioApplicationRequestHandlerIf | None = None
        self._refresh_handler: RadioRefreshRequestHandlerIf | None = None
        self._presets: list[RadioPreset] = []
        self._preset_buttons: list[tk.Button] = []
        self._poll_after_id: str | None = None
        self._active_preset: int | None = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = tk.Frame(self, bg=colors["status_bg"])
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        self._active_label = tk.Label(
            header,
            text="OFF",
            bg=colors["status_bg"],
            fg=colors["status_label"],
        )
        self._active_label.grid(row=0, column=0, padx=8, pady=6, sticky="w")

        self._signal_label = tk.Label(
            header,
            text="--",
            bg=colors["status_bg"],
            fg=colors["primary_value"],
            anchor="e",
        )
        self._signal_label.grid(row=0, column=1, padx=8, pady=6, sticky="e")

        body = tk.Frame(self, bg=colors["panel_bg"])
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        controls = tk.Frame(body, bg=colors["panel_bg"])
        controls.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        for column in range(2):
            controls.columnconfigure(column, weight=1)

        self._button(
            controls,
            panel_config.launch_tile.label,
            self._request_application_toggle,
        ).grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self._button(
            controls,
            panel_config.radio_toggle_tile.label,
            self._request_playback_toggle,
        ).grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        self._button(controls, "TUNE -", self._request_tune_down).grid(
            row=1, column=0, sticky="nsew", padx=2, pady=2
        )
        self._button(controls, "TUNE +", self._request_tune_up).grid(
            row=1, column=1, sticky="nsew", padx=2, pady=2
        )
        self._button(controls, "PREV", self._request_previous_station).grid(
            row=2, column=0, sticky="nsew", padx=2, pady=2
        )
        self._button(controls, "NEXT", self._request_next_station).grid(
            row=2, column=1, sticky="nsew", padx=2, pady=2
        )

        self._preset_frame = tk.Frame(body, bg=colors["panel_bg"])
        self._preset_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        for column in range(max(1, panel_config.preset_columns)):
            self._preset_frame.columnconfigure(column, weight=1)

    def _button(self, parent: tk.Misc, text: str, command: Callable[[], None]) -> tk.Button:
        colors = self._theme["colors"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=colors["tile_bg"],
            fg=colors["tile_title"],
            activebackground=colors["bank_button_active_bg"],
            activeforeground=colors["bank_button_active_fg"],
            relief=tk.FLAT,
            bd=0,
        )

    def start(self) -> None:
        """Start periodic semantic refresh requests."""
        self.stop_radio_status_polling()
        self._poll()

    def stop_radio_status_polling(self) -> None:
        """Stop periodic refresh requests."""
        if self._poll_after_id is not None:
            try:
                self.after_cancel(self._poll_after_id)
            except tk.TclError:
                pass
            self._poll_after_id = None

    def destroy(self) -> None:
        self.stop_radio_status_polling()
        super().destroy()

    def _poll(self) -> None:
        if self._refresh_handler is not None:
            self._refresh_handler.request_radio_refresh()
        interval_ms = int(self._theme.get("layout", {}).get("poll_interval_ms", 2000))
        self._poll_after_id = self.after(interval_ms, self._poll)

    def set_signal(self, signal: TunedSignal | None) -> None:
        if signal is None:
            self._signal_label.configure(text="--")
            return
        mhz = signal.frequency_hz / 1_000_000.0
        text = f"{mhz:.3f} MHz  {signal.mode.modulation.name}"
        if signal.rds_text:
            text += f"  {signal.rds_text}"
        self._signal_label.configure(text=text)
        if self._on_frequency_changed is not None:
            self._on_frequency_changed(signal.frequency_hz)

    def add_preset(self, preset: RadioPreset) -> None:
        index = len(self._presets)
        self._presets.append(preset)
        columns = max(1, self._config.preset_columns)
        button = self._button(
            self._preset_frame,
            preset.label,
            lambda value=index: self._request_preset(value),
        )
        button.grid(
            row=index // columns,
            column=index % columns,
            sticky="nsew",
            padx=2,
            pady=2,
        )
        self._preset_buttons.append(button)

    def clear_presets(self) -> None:
        for button in self._preset_buttons:
            button.destroy()
        self._preset_buttons.clear()
        self._presets.clear()
        self._active_preset = None

    def set_receiver_active(self, active: bool) -> None:
        self._active_label.configure(text="ON" if active else "OFF")

    def set_active_preset(self, preset_index: int | None) -> None:
        colors = self._theme["colors"]
        self._active_preset = preset_index
        for index, button in enumerate(self._preset_buttons):
            active = index == preset_index
            button.configure(
                bg=colors["active_preset_bg"] if active else colors["tile_bg"],
                fg=colors["active_preset_fg"] if active else colors["tile_title"],
            )

    def set_preset_request_handler(self, handler: PresetRequestHandlerIf | None) -> None:
        self._preset_handler = handler

    def set_playback_request_handler(self, handler: PlaybackRequestHandlerIf | None) -> None:
        self._playback_handler = handler

    def set_station_request_handler(self, handler: StationRequestHandlerIf | None) -> None:
        self._station_handler = handler

    def set_tuning_request_handler(self, handler: TuningRequestHandlerIf | None) -> None:
        self._tuning_handler = handler

    def set_application_request_handler(
        self,
        handler: RadioApplicationRequestHandlerIf | None,
    ) -> None:
        self._application_handler = handler

    def set_refresh_request_handler(
        self,
        handler: RadioRefreshRequestHandlerIf | None,
    ) -> None:
        self._refresh_handler = handler

    def _request_preset(self, index: int) -> None:
        if self._preset_handler is not None:
            self._preset_handler.request_preset(index)

    def _request_playback_toggle(self) -> None:
        if self._playback_handler is None:
            return
        if self._active_label.cget("text") == "ON":
            self._playback_handler.request_pause()
        else:
            self._playback_handler.request_play()

    def _request_application_toggle(self) -> None:
        if self._application_handler is not None:
            self._application_handler.request_toggle_radio_application()

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
