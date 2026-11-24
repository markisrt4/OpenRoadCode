# SPDX-License-Identifier: MIT
"""Session-local display controls for the native SDRForge radio UI.

These controls never connect to the legacy SDR++ remote-control port.
"""

from __future__ import annotations


class NativeRadioControl:
    """Retain presentation preferences independently of RF acquisition."""

    def __init__(self) -> None:
        self._waterfall = True
        self._bandplan = False
        self._fft_hold = False
        self._theme = "Dark"

    def waterfall_visible(self) -> bool:
        return self._waterfall

    def set_waterfall_visible(self, visible: bool) -> bool:
        self._waterfall = bool(visible)
        return self._waterfall

    def toggle_waterfall(self) -> bool:
        return self.set_waterfall_visible(not self._waterfall)

    def bandplan_visible(self) -> bool:
        return self._bandplan

    def set_bandplan_visible(self, visible: bool) -> bool:
        self._bandplan = bool(visible)
        return self._bandplan

    def toggle_bandplan(self) -> bool:
        return self.set_bandplan_visible(not self._bandplan)

    def fft_hold_enabled(self) -> bool:
        return self._fft_hold

    def set_fft_hold(self, enabled: bool) -> bool:
        self._fft_hold = bool(enabled)
        return self._fft_hold

    def toggle_fft_hold(self) -> bool:
        return self.set_fft_hold(not self._fft_hold)

    def auto_range(self) -> bool:
        # Native spectrum auto-ranging is handled by its renderer.
        return True

    def theme(self) -> str:
        return self._theme

    def themes(self) -> tuple[str, ...]:
        return ("Light", "Dark")

    def set_theme(self, theme: str) -> bool:
        if theme not in self.themes():
            return False
        self._theme = theme
        return True
