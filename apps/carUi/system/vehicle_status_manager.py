# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from ui.radio.radio_formatter import format_frequency
from ui.system import TopBarUiIf


class VehicleStatusManager:
    """Coordinate vehicle-related values with top-bar display updates."""

    def __init__(
        self,
        *,
        top_bar_ui: TopBarUiIf,
        empty_value: str = "--",
    ) -> None:
        self._top_bar_ui = top_bar_ui
        self._empty_value = empty_value

    def set_frequency(self, frequency_hz: int | None) -> None:
        text = (
            self._empty_value
            if frequency_hz is None
            else format_frequency(frequency_hz, precision=3)
        )
        self._top_bar_ui.set_frequency_text(text)

    def set_location(
        self,
        latitude: float | None,
        longitude: float | None,
    ) -> None:
        if latitude is None or longitude is None:
            self._top_bar_ui.set_location_text("🌎 lat.--, lon.--")
            return

        self._top_bar_ui.set_location_text(
            f"🌎 lat.{latitude:.2f}, lon.{longitude:.2f}"
        )
