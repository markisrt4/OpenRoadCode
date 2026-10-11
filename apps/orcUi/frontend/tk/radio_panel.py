# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""orcUi radio panel hosting and controlling external radio presentations."""

from __future__ import annotations

import tkinter as tk
from ui.radio.rf_radio_if import RadioAction, RadioHost, RadioRequest, RfRadioSession, RfRadioState
from ui.radio.radio_profile_state import RadioProfileState
from ui.theme import ThemeBundle
from .shell_metrics import FONT_SMALL
from .radio_display_controls import RadioDisplayControlsMixin
from .radio_group_menu import MAIN_GROUPS, RadioGroupMenuMixin

RADIO_GROUPS = tuple(name for name, _ in MAIN_GROUPS)

class RadioPanel(RadioGroupMenuMixin, RadioDisplayControlsMixin):
    """Automotive controls wrapped around embedded SDR++ and ADS-B views."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        session: RfRadioSession,
        theme: ThemeBundle,
    ) -> None:
        self._theme = theme
        ui = theme.ui
        super().__init__(parent, bg=ui.background)
        self._session = session
        self._telemetry_after_id: str | None = None
        self._active_group = "FM"
        self._state = RfRadioState(RadioProfileState("", 0, "", "", ""), ())
        self._group_buttons: dict[str, tk.Button] = {}
        self._drawer_open = False
        self._drawer: tk.Frame | None = None
        self._display_buttons: dict[str, tk.Button] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._groups = tk.Frame(
            self, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border
        )
        self._groups.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self._build_group_bar()
        self._body = tk.Frame(self, bg=ui.background)
        self._body.grid(row=1, column=0, sticky="nsew")
        self._body.grid_columnconfigure(0, weight=1)
        self._body.grid_rowconfigure(0, weight=1)
        self._host = tk.Frame(
            self._body, bg=ui.background, highlightthickness=1, highlightbackground=ui.border
        )
        self._host.grid(row=0, column=0, sticky="nsew")
        self._host.bind("<Configure>", self._on_host_resize)

        self._telemetry_overlay = tk.Frame(
            self._host, bg=ui.surface_alt, highlightthickness=1, highlightbackground=ui.border
        )
        self._telemetry_overlay.place(relx=1.0, x=-8, y=8, anchor="ne")
        self._signal_label = tk.Label(
            self._telemetry_overlay,
            text="SIGNAL --",
            bg=ui.surface_alt,
            fg=ui.text,
            font=("Monospace", 8, "bold"),
            padx=8,
            pady=3,
        )
        self._signal_label.pack(side=tk.LEFT)
        self._snr_label = tk.Label(
            self._telemetry_overlay,
            text="SNR --",
            bg=ui.surface_alt,
            fg=ui.accent_success,
            font=("Monospace", 8, "bold"),
            padx=8,
            pady=3,
        )
        self._snr_label.pack(side=tk.LEFT)

        self._controls = tk.Frame(
            self, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border
        )
        self._controls.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        self._controls.grid_columnconfigure(2, weight=1)
        tk.Button(
            self._controls,
            text="‹ PRESET",
            command=self._previous_preset,
            bg=ui.surface,
            fg=ui.text,
            activebackground=ui.control_background,
            activeforeground=ui.accent_success,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=7,
        ).grid(row=0, column=0, rowspan=3, sticky="ns")
        tk.Button(
            self._controls,
            text="− TUNE",
            command=self._tune_down,
            bg=ui.surface,
            fg=ui.text_muted,
            activebackground=ui.control_background,
            activeforeground=ui.accent_success,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=7,
        ).grid(row=0, column=1, rowspan=3, sticky="ns")
        center = tk.Frame(self._controls, bg=ui.surface)
        center.grid(row=0, column=2, rowspan=3, sticky="ew")
        self._station_label = tk.Label(
            center, text="NO PRESET", bg=ui.surface, fg=ui.text, font=("Sans", 11, "bold")
        )
        self._station_label.pack()
        self._frequency_label = tk.Label(
            center, text="--.- MHz", bg=ui.surface, fg=ui.text_muted, font=("Monospace", 9)
        )
        self._frequency_label.pack()
        self._metadata_label = tk.Label(
            center, text="", bg=ui.surface, fg=ui.accent_success, font=("Sans", FONT_SMALL)
        )
        self._metadata_label.pack()
        tk.Button(
            self._controls,
            text="TUNE +",
            command=self._tune_up,
            bg=ui.surface,
            fg=ui.text_muted,
            activebackground=ui.control_background,
            activeforeground=ui.accent_success,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=7,
        ).grid(row=0, column=3, rowspan=3, sticky="ns")
        tk.Button(
            self._controls,
            text="PRESET ›",
            command=self._next_preset,
            bg=ui.surface,
            fg=ui.text,
            activebackground=ui.control_background,
            activeforeground=ui.accent_success,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=7,
        ).grid(row=0, column=4, rowspan=3, sticky="ns")

        self._launch_status = tk.Label(self._host, text="Loading SDR++…", bg=ui.background,
                                       fg=ui.text, font=("Sans", 20, "bold"))
        self._session.bind(self)
        self._schedule_telemetry_refresh()

    def destroy(self) -> None:
        if self._telemetry_after_id is not None:
            try:
                self.after_cancel(self._telemetry_after_id)
            except tk.TclError:
                pass
            self._telemetry_after_id = None
        self._session.close()
        super().destroy()

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        """Repaint ORC radio chrome without disturbing the embedded X11 window."""
        self._theme = theme
        ui = theme.ui
        self.configure(bg=ui.background)
        self._groups.configure(bg=ui.surface, highlightbackground=ui.border)
        self._body.configure(bg=ui.background)
        self._host.configure(bg=ui.background, highlightbackground=ui.border)
        self._telemetry_overlay.configure(bg=ui.surface_alt, highlightbackground=ui.border)
        self._signal_label.configure(bg=ui.surface_alt, fg=ui.text)
        self._snr_label.configure(bg=ui.surface_alt, fg=ui.accent_success)
        self._controls.configure(bg=ui.surface, highlightbackground=ui.border)
        for child in self._controls.winfo_children():
            if isinstance(child, tk.Button):
                child.configure(
                    bg=ui.surface,
                    fg=ui.text,
                    activebackground=ui.control_background,
                    activeforeground=ui.accent_success,
                )
            elif isinstance(child, tk.Frame):
                child.configure(bg=ui.surface)
        self._station_label.configure(bg=ui.surface, fg=ui.text)
        self._frequency_label.configure(bg=ui.surface, fg=ui.text_muted)
        self._metadata_label.configure(bg=ui.surface, fg=ui.accent_success)
        if self._drawer is not None:
            self._drawer.destroy()
            self._drawer = None
            self._drawer_open = False
            self._display_buttons.clear()
        self._controls_button.configure(
            bg=ui.surface,
            fg=ui.text,
            activebackground=ui.control_background,
            activeforeground=ui.accent_success,
        )
        self._paint_groups()





    def _native_host(self) -> RadioHost:
        self.update_idletasks()
        return RadioHost(int(self._host.winfo_id()), int(self.winfo_toplevel().winfo_id()),
                         max(1, self._host.winfo_width()), max(1, self._host.winfo_height()),
                         self._host.winfo_rootx(), self._host.winfo_rooty())

    def launch(self) -> None:
        """Request RF startup without accessing a launcher from Tk."""
        self._session.request(RadioRequest(RadioAction.LAUNCH, host=self._native_host()))

    def show_adsb(self) -> None:
        self._show_adsb()

    def _show_adsb(self) -> None:
        self._active_group = "AIR:ADSB"
        self._paint_groups()
        self._session.request(RadioRequest(RadioAction.ADSB, host=self._native_host(),
                              color_scheme="light" if sum(self.winfo_rgb(self._theme.ui.background)) > 3 * 32767 else "dark"))

    @property
    def active_group(self) -> str:
        return self._active_group

    def select_group(self, name: str) -> None:
        if name not in RADIO_GROUPS:
            raise ValueError(f"Unknown radio group: {name}")
        self._active_group = name
        self._paint_groups()
        profiles = tuple(p for p in self._state.profiles if p.group == name)
        if profiles:
            self._session.request(RadioRequest(RadioAction.PROFILE, key=profiles[0].key))

    def set_station(self, label: str, frequency_hz: int, mode_name: str | None = None) -> None:
        self._station_label.configure(text=label)
        suffix = f"   {mode_name}" if mode_name else ""
        self._frequency_label.configure(text=f"{frequency_hz / 1_000_000:.3f} MHz{suffix}",
                                        fg=self._theme.ui.text_muted)

    def deactivate(self) -> None:
        self._session.deactivate()
        if self._telemetry_after_id is not None:
            self.after_cancel(self._telemetry_after_id)
            self._telemetry_after_id = None

    def detach_sdrpp(self, parent_window_id: int) -> None:
        self.deactivate()

    def _previous_preset(self) -> None:
        self._session.request(RadioRequest(RadioAction.PREVIOUS))

    def _next_preset(self) -> None:
        self._session.request(RadioRequest(RadioAction.NEXT))

    def _tune_down(self) -> None:
        self._session.request(RadioRequest(RadioAction.TUNE_DOWN))

    def _tune_up(self) -> None:
        self._session.request(RadioRequest(RadioAction.TUNE_UP))

    def set_radio_state(self, state: RfRadioState) -> None:
        self._state = state
        profile = next((p for p in state.profiles if p.key == state.station.profile_key), None)
        if state.view == "adsb":
            self._active_group = "AIR:ADSB"
        elif profile is not None:
            self._active_group = profile.group
        self._paint_groups()
        self.set_station(state.station.label, state.station.frequency_hz, state.station.mode_name)
        self._metadata_label.configure(text=state.telemetry.rds)
        signal = "--" if state.telemetry.signal_db is None else f"{state.telemetry.signal_db:.1f} dB"
        snr = "--" if state.telemetry.snr_db is None else f"{state.telemetry.snr_db:.1f} dB"
        self._signal_label.configure(text=f"SIGNAL {signal}")
        self._snr_label.configure(text=f"SNR {snr}")
        if state.loading or state.error:
            self._launch_status.configure(text=state.error or "Loading radio…",
                                          fg=self._theme.ui.accent_danger if state.error else self._theme.ui.text)
            self._launch_status.place(relx=0.5, rely=0.5, anchor="center")
            self._launch_status.lift()
        else:
            self._launch_status.place_forget()
        if state.view == "adsb":
            self._controls.grid_remove()
            self._telemetry_overlay.place_forget()
        else:
            self._controls.grid()
            self._telemetry_overlay.place(relx=1.0, x=-8, y=8, anchor="ne")
        self._controls_button.configure(state=tk.DISABLED if state.view == "adsb" else tk.NORMAL)
        self._refresh_display_controls()

    def _schedule_telemetry_refresh(self) -> None:
        self._session.request(RadioRequest(RadioAction.REFRESH))
        self._telemetry_after_id = self.after(500, self._schedule_telemetry_refresh)

    def _on_host_resize(self, event: tk.Event) -> None:
        self._session.request(RadioRequest(RadioAction.RESIZE, host=RadioHost(
            int(self._host.winfo_id()), int(self.winfo_toplevel().winfo_id()),
            max(1, event.width), max(1, event.height))))
