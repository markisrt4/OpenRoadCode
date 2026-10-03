# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""SDR++ display-control drawer behavior for the ORC radio panel."""

import tkinter as tk

from .shell_metrics import FONT_CONTROL


class RadioDisplayControlsMixin:
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
        try:
            themes = self._sdrpp.themes()
        except (OSError, RuntimeError, ValueError):
            return
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
            menu.add_command(label=theme, command=lambda value=theme: self._sdrpp.set_theme(value))
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

    def _remote_toggle(self, key: str, label: str, action) -> None:
        try:
            self._paint_toggle(key, label, action())
        except (OSError, RuntimeError, ValueError) as error:
            self._display_buttons[key].configure(
                text=f"{label}     !", fg=self._theme.ui.accent_danger
            )
            print(f"WARNING: SDR++ remote control: {type(error).__name__}: {error}")

    def _toggle_waterfall(self) -> None:
        self._remote_toggle("waterfall", "WATERFALL", self._sdrpp.toggle_waterfall)

    def _toggle_bandplan(self) -> None:
        self._remote_toggle("bandplan", "BANDPLAN", self._sdrpp.toggle_bandplan)

    def _toggle_fft_hold(self) -> None:
        self._remote_toggle("fft_hold", "PEAK HOLD", self._sdrpp.toggle_fft_hold)

    def _auto_range(self) -> None:
        try:
            self._sdrpp.auto_range()
        except (OSError, RuntimeError, ValueError) as error:
            print(f"WARNING: SDR++ auto range: {type(error).__name__}: {error}")

    def _refresh_display_controls(self) -> None:
        ui = self._theme.ui
        for key, label, getter in (
            ("waterfall", "WATERFALL", self._sdrpp.waterfall_visible),
            ("bandplan", "BANDPLAN", self._sdrpp.bandplan_visible),
            ("fft_hold", "PEAK HOLD", self._sdrpp.fft_hold_enabled),
        ):
            try:
                self._paint_toggle(key, label, getter())
            except (OSError, RuntimeError, ValueError):
                self._display_buttons[key].configure(text=label, fg=ui.text_muted, bg=ui.surface)
