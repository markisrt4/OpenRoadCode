# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""SDR++ display-control drawer behavior for the ORC radio panel."""

import tkinter as tk
from functools import partial

from ui.radio.rf_radio_if import RadioAction, RadioRequest

from .radio_presentation_frame import RadioPresentationFrame
from .shell_metrics import FONT_CONTROL


class RadioDisplayControlsMixin(RadioPresentationFrame):
    """Own the optional SDR++ display-controls drawer."""

    def _toggle_drawer(self) -> None:
        ui = self._theme.ui
        if self._drawer_open:
            if self._drawer is not None:
                self._drawer.place_forget()
            self._drawer_open = False
            self._controls_button.configure(fg=ui.text, bg=ui.surface)
            return
        if self._drawer is None:
            self._build_drawer()
        assert self._drawer is not None
        self._drawer.place(relx=1.0, rely=0.0, relheight=1.0, width=250, anchor="ne")
        self._drawer.lift()
        self._drawer_open = True
        self._controls_button.configure(fg=ui.accent_success, bg=ui.surface_alt)
        self._refresh_display_controls()

    def _build_drawer(self) -> None:
        ui = self._theme.ui
        self._drawer = tk.Frame(
            self._body, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border
        )
        header = tk.Frame(self._drawer, bg=ui.surface_alt)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="RADIO CONTROLS",
            bg=ui.surface_alt,
            fg=ui.text,
            font=("Sans", 11, "bold"),
            padx=12,
            pady=10,
        ).pack(side=tk.LEFT)
        tk.Button(
            header,
            text="✕",
            command=self._toggle_drawer,
            bg=ui.surface_alt,
            fg=ui.text_muted,
            activebackground=ui.control_background,
            activeforeground=ui.text,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=10,
        ).pack(side=tk.RIGHT)
        for key, label, action in (
            ("waterfall", "WATERFALL", self._toggle_waterfall),
            ("bandplan", "BANDPLAN", self._toggle_bandplan),
            ("fft_hold", "PEAK HOLD", self._toggle_fft_hold),
        ):
            button = tk.Button(
                self._drawer,
                text=label,
                command=action,
                anchor="w",
                bg=ui.surface,
                fg=ui.text_muted,
                activebackground=ui.control_background,
                activeforeground=ui.accent_success,
                relief=tk.FLAT,
                bd=0,
                font=("Sans", FONT_CONTROL, "bold"),
                padx=16,
                pady=11,
            )
            button.pack(fill=tk.X)
            self._display_buttons[key] = button
        tk.Frame(self._drawer, bg=ui.border, height=1).pack(fill=tk.X, padx=12, pady=4)
        tk.Button(
            self._drawer,
            text="AUTO RANGE",
            command=self._auto_range,
            anchor="w",
            bg=ui.surface,
            fg=ui.text,
            activebackground=ui.control_background,
            activeforeground=ui.text,
            relief=tk.FLAT,
            bd=0,
            padx=16,
            pady=11,
        ).pack(fill=tk.X)
        tk.Button(
            self._drawer,
            text="THEME…",
            command=self._choose_theme,
            anchor="w",
            bg=ui.surface,
            fg=ui.text,
            activebackground=ui.control_background,
            activeforeground=ui.text,
            relief=tk.FLAT,
            bd=0,
            padx=16,
            pady=11,
        ).pack(fill=tk.X)

    def _choose_theme(self) -> None:
        themes = self._state.themes
        if not themes:
            return
        ui = self._theme.ui
        menu = tk.Menu(
            self,
            tearoff=False,
            bg=ui.surface,
            fg=ui.text,
            activebackground=ui.control_background,
            activeforeground=ui.text,
        )
        for theme in themes:
            menu.add_command(label=theme, command=partial(self._session.request, RadioRequest(RadioAction.THEME, key=theme)))
        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()

    def _paint_toggle(self, key: str, label: str, enabled: bool) -> None:
        ui = self._theme.ui
        self._display_buttons[key].configure(
            text=f"{label}     {'ON' if enabled else 'OFF'}",
            fg=ui.accent_success if enabled else ui.text_muted,
            bg=ui.surface_alt if enabled else ui.surface,
        )

    def _toggle_waterfall(self) -> None:
        self._session.request(RadioRequest(RadioAction.WATERFALL))

    def _toggle_bandplan(self) -> None:
        self._session.request(RadioRequest(RadioAction.BANDPLAN))

    def _toggle_fft_hold(self) -> None:
        self._session.request(RadioRequest(RadioAction.FFT_HOLD))

    def _auto_range(self) -> None:
        self._session.request(RadioRequest(RadioAction.AUTO_RANGE))

    def _refresh_display_controls(self) -> None:
        for key, label, enabled in (
            ("waterfall", "WATERFALL", self._state.waterfall),
            ("bandplan", "BANDPLAN", self._state.bandplan),
            ("fft_hold", "PEAK HOLD", self._state.fft_hold),
        ):
            if key in self._display_buttons:
                self._paint_toggle(key, label, enabled)
