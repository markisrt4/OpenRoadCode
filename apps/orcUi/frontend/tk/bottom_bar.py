# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistent bottom controls for the integrated orcUi shell."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.theme import ThemeBundle
from ui.radio import AircraftMenuRequestHandlerIf, AircraftMenuUiState
from apps.orcUi.performance_status import PerformanceStatus
from .shell_metrics import (
    BOTTOM_BAR_HEIGHT,
    CONTROL_PAD_X,
    FONT_CONTROL,
    FONT_STATUS,
)


def aircraft_button_text(*, enabled: bool, aircraft_count: int) -> str:
    """Format the compact persistent Aircraft menu status."""
    del enabled, aircraft_count
    return "✈  AIRCRAFT ▾"


def aircraft_menu_labels(*, enabled: bool, aircraft_count: int) -> tuple[str, str, str]:
    """Describe Aircraft actions without coupling their behavior to Tk."""
    marker = "✓" if enabled else "○"
    receiver = f"{marker}  ADS-B receiver {'on' if enabled else 'off'}"
    count = max(0, aircraft_count)
    tracker = "↗  Open 1090 aircraft map"
    if enabled and count:
        tracker += f" · {count} nearby"
    return receiver, tracker, "♫  Open AM / pilot radio"


class OrcUiBottomBar(tk.Frame):
    """Own persistent volume, Aircraft, diagnostics, and theme controls."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        theme: ThemeBundle,
        volume_text: str,
        theme_label: str,
        on_volume_down: Callable[[], None],
        on_volume_up: Callable[[], None],
        on_theme_toggle: Callable[[], None],
        on_diagnostics: Callable[[], None],
    ) -> None:
        ui = theme.ui
        super().__init__(parent, bg=ui.background, height=BOTTOM_BAR_HEIGHT + 7)
        self._theme = theme
        self._adsb_enabled = False
        self._aircraft_count = 0
        self._aircraft_handler: AircraftMenuRequestHandlerIf | None = None
        self._aircraft_popup: tk.Frame | None = None

        self.grid_propagate(False)
        self.grid_rowconfigure(0, weight=1)
        for column in range(5):
            self.grid_columnconfigure(column, weight=1)

        volume = tk.Frame(
            self,
            bg=ui.surface,
            highlightthickness=0,
        )
        volume.grid(row=0, column=0, sticky="nsew", padx=CONTROL_PAD_X, pady=(7, 0))
        volume.grid_columnconfigure(0, minsize=42)
        volume.grid_columnconfigure(1, weight=1)
        volume.grid_columnconfigure(2, minsize=42)
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
            highlightthickness=0,
            font=("Sans", FONT_STATUS + 3, "bold"),
        ).grid(row=0, column=0, sticky="nsew", padx=(3, 2), pady=3)
        self._volume_label = tk.Label(
            volume,
            text=volume_text,
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", FONT_STATUS, "bold"),
        )
        self._volume_label.grid(row=0, column=1, sticky="nsew", pady=3)
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
            highlightthickness=0,
            font=("Sans", FONT_STATUS + 3, "bold"),
        ).grid(row=0, column=2, sticky="nsew", padx=(2, 3), pady=3)

        self._aircraft_button = self._button(self._show_aircraft_menu, bold=True)
        self._aircraft_button.grid(
            row=0, column=1, sticky="nsew",
            padx=CONTROL_PAD_X, pady=(7, 0),
        )
        theme_button = self._button(on_theme_toggle, bold=True)
        theme_button.configure(text=theme_label)
        self._performance_button = self._button(on_diagnostics, bold=True)
        self._performance_button.configure(cursor="hand2")
        self._performance_button.grid(row=0, column=2, sticky="nsew", padx=CONTROL_PAD_X, pady=(7, 0))
        self.set_performance_status(PerformanceStatus())
        theme_button.grid(row=0, column=3, sticky="nsew", padx=CONTROL_PAD_X, pady=(7, 0))
        self._paint_adsb()

    def _button(
        self,
        command: Callable[[], None],
        *,
        bold: bool,
        parent: tk.Misc | None = None,
    ) -> tk.Button:
        ui = self._theme.ui
        weight = "bold" if bold else "normal"
        return tk.Button(
            parent if parent is not None else self,
            command=command,
            bg=ui.control_background,
            fg=ui.control_text,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            font=("Sans", FONT_CONTROL, weight),
        )

    def set_performance_status(self, status: PerformanceStatus) -> None:
        """Present observed computing-unit health alongside the shell controls."""
        self._performance_button.configure(text=status.text, fg=getattr(self._theme.ui, status.tone))

    def set_volume_text(self, text: str) -> None:
        self._volume_label.configure(text=text)

    def set_aircraft_request_handler(self, handler: AircraftMenuRequestHandlerIf | None) -> None:
        self._aircraft_handler = handler

    def set_aircraft_state(self, state: AircraftMenuUiState) -> None:
        self._adsb_enabled = bool(state.adsb_enabled)
        self._aircraft_count = max(0, int(state.aircraft_count))
        self._paint_adsb()

    def _toggle_adsb(self) -> None:
        handler = self._aircraft_handler
        if handler is None:
            return
        handler.request_adsb_enabled(not self._adsb_enabled)

    def _show_aircraft(self) -> None:
        if self._aircraft_handler is not None:
            self._aircraft_handler.request_open_tracker()

    def _show_aircraft_menu(self) -> None:
        if self._aircraft_popup is not None:
            self._close_aircraft_menu()
            return
        ui = self._theme.ui
        receiver, tracker, airband = aircraft_menu_labels(
            enabled=self._adsb_enabled,
            aircraft_count=self._aircraft_count,
        )
        root = self.winfo_toplevel()
        popup = tk.Frame(root, bg=ui.surface, bd=0, highlightthickness=0)
        self._aircraft_popup = popup
        for label, action in (
            (receiver, self._toggle_adsb),
            (tracker, self._show_aircraft),
            (airband, self._show_airband),
        ):
            tk.Button(
                popup,
                text=label,
                command=lambda selected=action: self._run_aircraft_action(selected),
                state=tk.NORMAL if self._aircraft_handler is not None else tk.DISABLED,
                bg=ui.control_background,
                fg=ui.text,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                bd=0,
                highlightthickness=0,
                anchor="w",
                font=("Sans", FONT_CONTROL),
                padx=14,
                pady=9,
            ).pack(fill=tk.X, pady=(0, 2))
        self.update_idletasks()
        popup.update_idletasks()
        x = self._aircraft_button.winfo_rootx() - root.winfo_rootx()
        y = self._aircraft_button.winfo_rooty() - root.winfo_rooty() - popup.winfo_reqheight()
        popup.place(x=x, y=max(0, y), width=max(
            self._aircraft_button.winfo_width(), popup.winfo_reqwidth()
        ))
        popup.lift()

    def _run_aircraft_action(self, action: Callable[[], None]) -> None:
        self._close_aircraft_menu()
        action()

    def _close_aircraft_menu(self) -> None:
        popup = self._aircraft_popup
        self._aircraft_popup = None
        if popup is not None:
            popup.destroy()

    def destroy(self) -> None:
        self._close_aircraft_menu()
        super().destroy()

    def _show_airband(self) -> None:
        if self._aircraft_handler is not None:
            self._aircraft_handler.request_open_airband()

    def _paint_adsb(self) -> None:
        ui = self._theme.ui
        self._aircraft_button.configure(
            text=aircraft_button_text(
                enabled=self._adsb_enabled,
                aircraft_count=self._aircraft_count,
            ),
            state=tk.NORMAL,
            fg=ui.accent_success if self._adsb_enabled else ui.control_text,
        )
