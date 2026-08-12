# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Multi-band radio destination for Car TUI."""

import curses

from apps.carTui.radio_catalog import CarTuiRadio
from frontends.tui.radio import RadioDashboardView


class RadioScreen:
    """Route user controls to one of four radio controllers."""

    def __init__(self, radios: tuple[CarTuiRadio, ...], refresh_seconds: float = 0.5) -> None:
        if not radios:
            raise ValueError("at least one radio is required")
        self._radios = radios
        self._selected = 0
        self._refresh_seconds = refresh_seconds
        self._view = RadioDashboardView()

    def run(self, window) -> bool:
        """Run until back or quit; return False when the app should quit."""
        status = self._availability_status()
        window.timeout(max(1, int(self._refresh_seconds * 1000)))
        try:
            while True:
                radio = self._radios[self._selected]
                controller = radio.controller
                signal = snr = rds = None
                if controller.is_started:
                    try:
                        signal = controller.get_signal_strength()
                        snr = controller.get_snr()
                        rds = controller.get_rds()
                    except Exception:
                        status = "Receiver telemetry unavailable"
                frequency = controller.get_frequency() if controller.is_started else None
                preset_index = getattr(controller, "current_preset_index", None)
                mode = getattr(getattr(controller, "current_mode", None), "name", "")
                self._view.render(
                    window,
                    labels=tuple(item.label for item in self._radios),
                    selected_index=self._selected,
                    frequency_hz=frequency,
                    mode_name=mode,
                    presets=controller.presets,
                    selected_preset_index=preset_index,
                    started=controller.is_started,
                    status=status,
                    signal_strength=signal,
                    snr=snr,
                    rds=rds,
                )
                key = window.getch()
                if key in (ord("q"), ord("Q")):
                    return False
                if key in (ord("b"), ord("B"), 27):
                    return True
                if ord("1") <= key <= ord(str(min(9, len(self._radios)))):
                    self._select(key - ord("1"))
                    status = self._availability_status()
                elif key in (ord("p"), ord("P")):
                    status = self._toggle_power()
                elif controller.is_started and key == curses.KEY_RIGHT:
                    controller.frequency_up()
                    status = "Tuned up"
                elif controller.is_started and key == curses.KEY_LEFT:
                    controller.frequency_down()
                    status = "Tuned down"
                elif controller.is_started and key == ord("]"):
                    status = f"Preset: {controller.next_preset().label}"
                elif controller.is_started and key == ord("["):
                    status = f"Preset: {controller.previous_preset().label}"
        finally:
            window.timeout(-1)
            for radio in self._radios:
                radio.controller.stop()

    def _select(self, index: int) -> None:
        if index == self._selected:
            return
        self._radios[self._selected].controller.stop()
        self._selected = index

    def _toggle_power(self) -> str:
        controller = self._radios[self._selected].controller
        if controller.is_started:
            controller.stop()
            return "Receiver stopped"
        if not controller.is_available:
            return controller.status_message or "Receiver unavailable"
        try:
            controller.start()
            return "Receiver started"
        except Exception:
            return "Unable to start receiver"

    def _availability_status(self) -> str:
        controller = self._radios[self._selected].controller
        return controller.status_message or "Press p to start receiver"
