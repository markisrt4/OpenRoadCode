# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistent bottom controls for the integrated orcUi shell."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.theme import ThemeBundle


class OrcUiBottomBar(tk.Frame):
    """Own persistent volume, ADS-B, settings, and theme controls."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        theme: ThemeBundle,
        volume_text: str,
        theme_label: str,
        on_volume_down: Callable[[], None],
        on_volume_up: Callable[[], None],
        on_settings: Callable[[], None],
        on_theme_toggle: Callable[[], None],
    ) -> None:
        ui = theme.ui
        super().__init__(parent, bg=ui.background, height=55)
        self._theme = theme
        self._adsb_enabled = False
        self._aircraft_count = 0
        self._adsb_toggle_handler: Callable[[bool], bool] | None = None
        self._adsb_view_handler: Callable[[], None] | None = None

        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=2)
        for column in range(1, 6):
            self.grid_columnconfigure(column, weight=1)

        volume = tk.Frame(
            self,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        volume.grid(row=0, column=0, sticky="nsew", padx=3)
        volume.grid_columnconfigure(1, weight=1)
        tk.Button(
            volume,
            text="−",
            command=on_volume_down,
            bg=ui.control_background,
            fg=ui.control_text,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 16, "bold"),
        ).grid(row=0, column=0, sticky="ns", padx=4)
        self._volume_label = tk.Label(
            volume,
            text=volume_text,
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", 10, "bold"),
        )
        self._volume_label.grid(row=0, column=1)
        tk.Button(
            volume,
            text="+",
            command=on_volume_up,
            bg=ui.control_background,
            fg=ui.control_text,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 15, "bold"),
        ).grid(row=0, column=2, sticky="ns", padx=4)

        self._adsb_toggle_button = self._button(self._toggle_adsb, bold=True)
        self._adsb_toggle_button.grid(row=0, column=1, sticky="nsew", padx=3)
        self._aircraft_button = self._button(self._show_aircraft, bold=True)
        self._aircraft_button.grid(row=0, column=2, sticky="nsew", padx=3)
        settings = self._button(on_settings, bold=True)
        settings.configure(text="⚙  SETTINGS")
        settings.grid(row=0, column=3, sticky="nsew", padx=3)
        theme_button = self._button(on_theme_toggle, bold=True)
        theme_button.configure(text=theme_label)
        theme_button.grid(row=0, column=4, columnspan=2, sticky="nsew", padx=3)
        self._paint_adsb()

    def _button(self, command: Callable[[], None], *, bold: bool) -> tk.Button:
        ui = self._theme.ui
        weight = "bold" if bold else "normal"
        return tk.Button(
            self,
            command=command,
            bg=ui.control_background,
            fg=ui.control_text,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=ui.border,
            font=("Sans", 9, weight),
        )

    def set_volume_text(self, text: str) -> None:
        self._volume_label.configure(text=text)

    def set_adsb_handlers(
        self,
        *,
        on_toggle: Callable[[bool], bool],
        on_view: Callable[[], None],
    ) -> None:
        self._adsb_toggle_handler = on_toggle
        self._adsb_view_handler = on_view

    def set_adsb_state(self, *, enabled: bool, aircraft_count: int) -> None:
        self._adsb_enabled = bool(enabled)
        self._aircraft_count = max(0, int(aircraft_count))
        self._paint_adsb()

    def _toggle_adsb(self) -> None:
        handler = self._adsb_toggle_handler
        if handler is None:
            return
        enabled = handler(not self._adsb_enabled)
        self.set_adsb_state(enabled=enabled, aircraft_count=self._aircraft_count)

    def _show_aircraft(self) -> None:
        if self._adsb_enabled and self._adsb_view_handler is not None:
            self._adsb_view_handler()

    def _paint_adsb(self) -> None:
        ui = self._theme.ui
        self._adsb_toggle_button.configure(
            text="✈  ADS-B ON" if self._adsb_enabled else "✈  ADS-B OFF",
            fg=ui.accent_success if self._adsb_enabled else ui.control_text,
        )
        self._aircraft_button.configure(
            text=(
                f"▣  AIRCRAFT {self._aircraft_count}"
                if self._adsb_enabled
                else "▣  AIRCRAFT --"
            ),
            state=tk.NORMAL if self._adsb_enabled else tk.DISABLED,
            fg=ui.control_text if self._adsb_enabled else ui.text_muted,
        )
