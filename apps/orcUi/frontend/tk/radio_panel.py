# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""orcUi radio panel hosting and controlling external radio presentations."""

from __future__ import annotations

import tkinter as tk
from .sdrforge_receiver_view import SdrForgeReceiverView
from .automotive_radio_button import AutomotiveRadioButton
from ui.radio.sdrforge_spectrum_if import SpectrumPresentation
from ui.radio.radio_visualization_config import RadioVisualizationConfig
from ui.radio.rf_radio_if import RadioAction, RadioHost, RadioRequest, RfRadioSession, RfRadioState, receiver_mode_mismatch
from ui.radio.radio_profile_state import RadioProfileState
from ui.theme import ThemeBundle
from .shell_metrics import FONT_SMALL
from .radio_display_controls import RadioDisplayControlsMixin
from .radio_group_menu import MAIN_GROUPS, RadioGroupMenuMixin

RADIO_GROUPS = tuple(name for name, _ in MAIN_GROUPS)

def receiver_sidebar_width(panel_width: int) -> int:
    """Reserve room for the FFT while scaling the controls on smaller windows."""
    return max(240, min(320, panel_width // 4))



class RadioPanel(RadioGroupMenuMixin, RadioDisplayControlsMixin):
    """Automotive controls wrapped around embedded SDR++ and ADS-B views."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        session: RfRadioSession,
        theme: ThemeBundle,
        native_sdrforge: bool = False,
        visualization: RadioVisualizationConfig | None = None,
    ) -> None:
        self._theme = theme
        self._driving_radio = native_sdrforge
        ui = theme.ui
        super().__init__(parent, bg=ui.background)
        self._session = session
        self._telemetry_after_id: str | None = None
        self._active_group = "FM"
        self._pending_group: str | None = None
        self._state = RfRadioState(RadioProfileState("", 0, "", "", ""), ())
        self._group_buttons: dict[str, tk.Button] = {}
        self._drawer_open = False
        self._drawer: tk.Frame | None = None
        self._display_buttons: dict[str, tk.Button] = {}
        self._live_rf_buttons: list[AutomotiveRadioButton] = []
        self._receiver_start_pending = False
        self._last_receiver_running: bool | None = None
        self._favorites_signature = None
        self._preset_page = 0
        self._preset_page_size = 4

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._groups = tk.Frame(
            self, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border
        )
        self._groups.grid(row=0, column=0, sticky="ew", pady=(0, 3))
        self._subcategory_strip = tk.Frame(self, bg=ui.surface)
        self._subcategory_signature = None

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
        self._sdrforge_view: SdrForgeReceiverView | None = None
        self._sdrforge_after_id: str | None = None
        if native_sdrforge:
            self._sdrforge_view = SdrForgeReceiverView(self._host, theme=theme,
                                                      visualization=visualization)
            self._sdrforge_view.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._sdrforge_view.set_spectrum_tune_handler(self._tune_spectrum_frequency)
            self._poll_sdrforge_spectrum()

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
        self._controls.grid(row=2, column=0, sticky="ew", pady=(2, 0))
        for column in range(5):
            self._controls.grid_columnconfigure(column, weight=1 if native_sdrforge else (1 if column == 2 else 0))
        tk.Button(
            self._controls,
            text="◀  STATION",
            command=self._previous_preset,
            bg=ui.surface,
            fg=ui.text,
            activebackground=ui.control_background,
            activeforeground=ui.accent_success,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=12 if native_sdrforge else 7,
            highlightthickness=0,
        ).grid(row=0, column=0, rowspan=3, sticky="nsew" if native_sdrforge else "ns")
        tk.Button(
            self._controls,
            text="◀  TUNE",
            command=self._tune_down,
            bg=ui.surface,
            fg=ui.text_muted,
            activebackground=ui.control_background,
            activeforeground=ui.accent_success,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=12 if native_sdrforge else 7,
            highlightthickness=0,
        ).grid(row=0, column=1, rowspan=3, sticky="nsew" if native_sdrforge else "ns")
        center = tk.Frame(self._controls, bg=ui.surface)
        center.grid(row=0, column=2, rowspan=3, sticky="ew")
        self._station_label = tk.Label(
            center, text="FM RADIO", bg=ui.surface, fg=ui.text, font=("Sans", 15, "bold")
        )
        self._station_label.pack()
        self._frequency_label = tk.Label(
            center, text="--.--- MHz", bg=ui.surface, fg=ui.text_muted, font=("Monospace", 9)
        )
        self._frequency_label.pack()
        self._metadata_label = tk.Label(
            center, text="", bg=ui.surface, fg=ui.accent_success, font=("Sans", FONT_SMALL)
        )
        self._metadata_label.pack()
        if native_sdrforge:
            center.grid_remove()  # Frequency and station already appear in the receiver header.
            self._controls.grid_columnconfigure(2, weight=0, minsize=0)
        tk.Button(
            self._controls,
            text="TUNE  ▶",
            command=self._tune_up,
            bg=ui.surface,
            fg=ui.text_muted,
            activebackground=ui.control_background,
            activeforeground=ui.accent_success,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=7,
            highlightthickness=0,
        ).grid(row=0, column=3, rowspan=3, sticky="nsew" if native_sdrforge else "ns")
        tk.Button(
            self._controls,
            text="STATION  ▶",
            command=self._next_preset,
            bg=ui.surface,
            fg=ui.text,
            activebackground=ui.control_background,
            activeforeground=ui.accent_success,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=7,
            highlightthickness=0,
        ).grid(row=0, column=4, rowspan=3, sticky="nsew" if native_sdrforge else "ns")

        self._receiver_controls = None
        if native_sdrforge:
            self._controls.grid_remove()
            # Keep a generous FFT viewport at 1280x720 while allowing smaller
            # windowed launches to retain usable tuning controls.
            self._body.grid_columnconfigure(1, weight=0, minsize=320)
            self.bind("<Configure>", self._resize_receiver_sidebar, add="+")
            self._receiver_controls = tk.Frame(
                self._body, bg=ui.surface, width=320,
                highlightthickness=1, highlightbackground=ui.border)
            self._receiver_controls.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
            self._receiver_controls.grid_propagate(False)
            self._receiver_controls.grid_rowconfigure(1, minsize=132)
            for col in (0, 1):
                self._receiver_controls.grid_columnconfigure(col, weight=1, uniform="tuning")
            self._subcategory_strip = tk.Frame(self._receiver_controls, bg=ui.surface)
            self._subcategory_strip.grid(row=1, column=0, columnspan=2,
                                         sticky="new", padx=5, pady=(0, 4))
            for tile_column in range(2):
                self._subcategory_strip.grid_columnconfigure(tile_column, weight=1,
                                                               uniform="bands")
            self._station_info = tk.Frame(self._receiver_controls, bg=ui.surface)
            self._station_info.grid(row=1, column=0, columnspan=2,
                                    sticky="nsew", padx=8, pady=4)
            self._info_title = tk.Label(self._station_info, text="RDS  •  WAITING",
                                        bg=ui.surface, fg=ui.accent_primary,
                                        font=("Sans", 10, "bold"), anchor="w")
            self._info_title.pack(fill=tk.X)
            self._info_name = tk.Label(self._station_info, text="No station ID",
                                       bg=ui.surface, fg=ui.text,
                                       font=("Sans", 13, "bold"), anchor="w")
            self._info_name.pack(fill=tk.X)
            self._info_text = tk.Label(self._station_info, text="Waiting for RDS data",
                                       bg=ui.surface, fg=ui.text_muted,
                                       font=("Sans", 9), anchor="nw", justify="left",
                                       wraplength=288)
            self._info_text.pack(fill=tk.X)
            self._bands_heading = tk.Label(self._receiver_controls, text="BANDS", bg=ui.surface,
                     fg=ui.accent_primary, font=("Sans", 11, "bold"),
                     anchor="w", padx=10, pady=2)
            self._bands_heading.grid(row=0, column=0, columnspan=2, sticky="ew")
            tk.Label(self._receiver_controls, text="TUNING", bg=ui.surface,
                     fg=ui.accent_primary, font=("Sans", 10, "bold"),
                     anchor="w", padx=10, pady=2).grid(
                         row=2, column=0, columnspan=2, sticky="ew")
            for label, callback, row, col in (
                ("◀  STEP −", self._tune_down, 3, 0),
                ("+ STEP  ▶", self._tune_up, 3, 1),
                ("◀  PRESET", self._previous_preset, 4, 0),
                ("PRESET  ▶", self._next_preset, 4, 1),
            ):
                button = AutomotiveRadioButton(self._receiver_controls, text=label,
                                      command=callback, height=44,
                                      background=ui.control_background,
                                      accent=ui.accent_primary,
                                      foreground=ui.text, border=ui.border)
                button.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)
                button.set_enabled(False)
                self._live_rf_buttons.append(button)
            self._scan_button = AutomotiveRadioButton(
                self._receiver_controls, text="SCAN BAND", command=self._toggle_scan,
                height=44, background=ui.control_background,
                accent=ui.accent_primary, foreground=ui.text, border=ui.border)
            self._scan_button.grid(row=5, column=0, sticky="nsew", padx=2, pady=2)
            self._scan_button.set_enabled(False)
            self._live_rf_buttons.append(self._scan_button)
            self._play_button = AutomotiveRadioButton(
                self._receiver_controls, text="🔇 MUTE", command=self._toggle_play,
                height=44, background=ui.control_background,
                accent=ui.accent_primary, foreground=ui.text, border=ui.border)
            self._play_button.grid(row=5, column=1, sticky="nsew", padx=2, pady=2)
            self._play_button.set_enabled(False)
            self._live_rf_buttons.append(self._play_button)
            self._receiver_power_button = AutomotiveRadioButton(
                self._receiver_controls, text="▶ START SDR",
                command=self._toggle_receiver_power,
                height=44, background=ui.control_background,
                accent=ui.accent_primary, foreground=ui.text, border=ui.border)
            self._receiver_power_button.grid(
                row=6, column=0, columnspan=2, sticky="nsew", padx=2, pady=2)
            self._receiver_mode_label = tk.Label(
                self._receiver_controls, text="MODE  --", bg=ui.surface,
                fg=ui.text_muted, font=("Sans", 9), anchor="w", padx=8, pady=2)
            self._receiver_mode_label.grid(row=8, column=0, columnspan=2, sticky="ew")
            # This row is informational; no new controls or scrollbars are needed.
            self._receiver_signal_label = tk.Label(
                self._receiver_controls, text="SIGNAL  --", bg=ui.surface,
                fg=ui.text_muted, font=("Sans", 10), anchor="w", padx=12, pady=8)
            self._receiver_signal_label.grid(row=7, column=0, columnspan=2, sticky="ew")

        self._favorites = tk.Frame(self, bg=ui.surface)
        if native_sdrforge:
            self._favorites.grid(row=3, column=0, sticky="ew", pady=(2, 0))
        self._launch_status = tk.Label(self._host, text="Connecting to radio…", bg=ui.background,
                                       fg=ui.text, font=("Sans", 20, "bold"))
        self._session.bind(self)
        self._schedule_telemetry_refresh()

    def _resize_receiver_sidebar(self, event: tk.Event) -> None:
        """Keep the waterfall dominant as the radio panel is resized."""
        if event.widget is not self or self._receiver_controls is None:
            return
        width = receiver_sidebar_width(event.width)
        if self._receiver_controls.winfo_reqwidth() != width:
            self._receiver_controls.configure(width=width)
            self._body.grid_columnconfigure(1, minsize=width)
            self._info_text.configure(wraplength=max(180, width - 32))

    def _poll_sdrforge_spectrum(self) -> None:
        if self._sdrforge_view is not None:
            self._session.refresh_spectrum()
            self._sdrforge_after_id = self.after(100, self._poll_sdrforge_spectrum)

    def set_spectrum_presentation(self, snapshot: SpectrumPresentation) -> None:
        if self._sdrforge_view is not None:
            self._sdrforge_view.set_spectrum(
                snapshot.bins,
                center_frequency_hz=snapshot.center_frequency_hz,
                sample_rate_hz=snapshot.sample_rate_hz,
                power_db=snapshot.power_db,
            )

    def destroy(self) -> None:
        if self._sdrforge_after_id is not None:
            self.after_cancel(self._sdrforge_after_id)
            self._sdrforge_after_id = None
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
        if self._receiver_controls is not None:
            self._receiver_controls.configure(bg=ui.surface, highlightbackground=ui.border)
        self._favorites.configure(bg=ui.surface)
        self._subcategory_strip.configure(bg=ui.surface)
        if self._receiver_controls is not None:
            for child in self._receiver_controls.winfo_children():
                if isinstance(child, AutomotiveRadioButton):
                    child.set_palette(background=ui.control_background,
                                      accent=ui.accent_primary,
                                      foreground=ui.text, border=ui.border)
                elif isinstance(child, tk.Label):
                    child.configure(bg=ui.surface, fg=ui.text)

        self._subcategory_signature = None
        if self._sdrforge_view is not None:
            self._render_subcategory_tiles(self._state)
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
        if self._receiver_controls is not None:
            # Reapply dynamic warning colors after a light/dark theme switch.
            self._receiver_mode_label.configure(
                fg=ui.accent_danger if receiver_mode_mismatch(self._state)
                else ui.text_muted,
            )
        if self._sdrforge_view is not None:
            self._sdrforge_view.set_theme_bundle(theme)

    def _render_subcategory_tiles(self, state: RfRadioState) -> None:
        """One-touch subcategory selection, with no popup or nested menus."""
        group = self._active_group.split(":", 1)[0]
        profiles = tuple(p for p in state.profiles if p.group == group)
        signature = (group, tuple((p.key, p.label) for p in profiles),
                     state.station.profile_key)
        if signature == self._subcategory_signature:
            return
        self._subcategory_signature = signature
        for child in self._subcategory_strip.winfo_children():
            child.destroy()
        ui = self._theme.ui
        show_bands = group not in ("FM", "WEATHER")
        if self._receiver_controls is not None:
            self._bands_heading.configure(text="BANDS" if show_bands else "")
        if self._receiver_controls is not None:
            if show_bands:
                self._bands_heading.grid()
                self._subcategory_strip.grid()
            else:
                # Keep the reserved band bay mapped so tuning never moves.
                self._bands_heading.grid()
                self._subcategory_strip.grid()
        for index, profile in enumerate(profiles if show_bands else ()):
            row, col = divmod(index, 2)
            selected = profile.key == state.station.profile_key
            AutomotiveRadioButton(
                self._subcategory_strip, text=profile.label,
                command=lambda key=profile.key: self._session.request(
                    RadioRequest(RadioAction.PROFILE, key=key)),
                selected=selected, height=40, background=ui.control_background,
                accent=ui.accent_primary, foreground=ui.text, border=ui.border,
            ).grid(row=row, column=col, sticky="nsew", padx=2, pady=1)
            self._subcategory_strip.grid_columnconfigure(col, weight=1, uniform="profiles")
        if group == "AIR":
            row, col = divmod(len(profiles), 2)
            AutomotiveRadioButton(
                self._subcategory_strip, text="ADS-B MAP",
                command=self._show_adsb, selected=self._active_group == "AIR:ADSB",
                height=40, background=ui.control_background,
                accent=ui.accent_primary, foreground=ui.text, border=ui.border,
            ).grid(row=row, column=col, sticky="nsew", padx=2, pady=1)
            self._subcategory_strip.grid_columnconfigure(col, weight=1, uniform="profiles")

    def _native_host(self) -> RadioHost:
        self.update_idletasks()
        return RadioHost(int(self._host.winfo_id()), int(self.winfo_toplevel().winfo_id()),
                         max(1, self._host.winfo_width()), max(1, self._host.winfo_height()),
                         self._host.winfo_rootx(), self._host.winfo_rooty())

    def launch(self) -> None:
        """Request RF startup without accessing a launcher from Tk."""
        if self._sdrforge_view is None:
            self._session.request(RadioRequest(RadioAction.LAUNCH, host=self._native_host()))

    def show_adsb(self) -> None:
        self._show_adsb()

    def _show_adsb(self) -> None:
        self._active_group = "AIR:ADSB"
        self._paint_groups()
        if self._sdrforge_view is not None:
            self._sdrforge_view.place_forget()
        self._session.request(RadioRequest(RadioAction.ADSB, host=self._native_host(),
                              color_scheme="light" if sum(self.winfo_rgb(self._theme.ui.background)) > 3 * 32767 else "dark"))

    @property
    def active_group(self) -> str:
        return self._active_group

    def select_group(self, name: str) -> None:
        if name not in RADIO_GROUPS:
            raise ValueError(f"Unknown radio group: {name}")
        self._active_group = name
        self._pending_group = name
        self._paint_groups()
        if self._sdrforge_view is not None:
            self._render_subcategory_tiles(self._state)
        profiles = tuple(p for p in self._state.profiles if p.group == name)
        if name == "AIR" and not profiles:
            self._show_adsb()
        elif profiles:
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

    def _toggle_receiver_power(self) -> None:
        if self._receiver_start_pending or self._state.receiver_starting:
            return
        if not self._state.receiver_running:
            self._receiver_start_pending = True
            self._receiver_power_button.set_text("STARTING SDR…")
            self._receiver_power_button.set_enabled(False)
        action = (RadioAction.STOP_RECEIVER if self._state.receiver_running
                  else RadioAction.START_RECEIVER)
        self._session.request(RadioRequest(action))

    def _toggle_play(self) -> None:
        if self._sdrforge_view is not None and not self._state.receiver_running:
            return
        action = RadioAction.PAUSE if self._state.playing else RadioAction.PLAY
        self._session.request(RadioRequest(action))

    def _toggle_scan(self) -> None:
        if self._sdrforge_view is not None and not self._state.receiver_running:
            return
        action = RadioAction.STOP_SCAN if self._state.scanning else RadioAction.SCAN
        self._session.request(RadioRequest(action))

    def _previous_preset(self) -> None:
        if self._sdrforge_view is not None and not self._state.receiver_running:
            return
        self._session.request(RadioRequest(RadioAction.PREVIOUS))

    def _next_preset(self) -> None:
        if self._sdrforge_view is not None and not self._state.receiver_running:
            return
        self._session.request(RadioRequest(RadioAction.NEXT))

    def _tune_spectrum_frequency(self, frequency_hz: int) -> None:
        if self._state.receiver_running and self._state.view != "adsb":
            self._session.request(RadioRequest(
                RadioAction.TUNE_FREQUENCY, frequency_hz=frequency_hz))

    def _tune_down(self) -> None:
        if self._sdrforge_view is not None and not self._state.receiver_running:
            return
        self._session.request(RadioRequest(RadioAction.TUNE_DOWN))

    def _tune_up(self) -> None:
        if self._sdrforge_view is not None and not self._state.receiver_running:
            return
        self._session.request(RadioRequest(RadioAction.TUNE_UP))

    def auto_range_spectrum(self) -> None:
        """Reset native spectrum scaling without contacting SDR++."""
        if self._sdrforge_view is not None:
            self._sdrforge_view.auto_range()

    def set_radio_state(self, state: RfRadioState) -> None:
        if (self._sdrforge_view is not None
                and state.receiver_running is False
                and self._last_receiver_running is not False):
            self._sdrforge_view.clear_spectrum()
        self._last_receiver_running = state.receiver_running
        self._state = state
        if self._sdrforge_view is not None:
            self._sdrforge_view.set_display_controls(
                waterfall=state.waterfall, peak_hold=state.fft_hold)
        # The backend's starting flag takes precedence over the local click
        # latch. Keep the button disabled until acquisition succeeds or fails.
        if state.receiver_running or state.receiver_starting or state.error:
            self._receiver_start_pending = False
        profile = next((p for p in state.profiles if p.key == state.station.profile_key), None)
        if state.view == "adsb":
            self._active_group = "AIR:ADSB"
        elif profile is not None:
            if self._pending_group is None or profile.group == self._pending_group:
                self._active_group = profile.group
                self._pending_group = None
        self._paint_groups()
        if self._sdrforge_view is not None:
            self._render_subcategory_tiles(state)
        if self._sdrforge_view is not None:
            self._render_favorites(state)
        self.set_station(state.station.label, state.station.frequency_hz, state.station.mode_name)
        self._metadata_label.configure(text=state.telemetry.radio_text or state.telemetry.rds)
        if self._sdrforge_view is not None and state.view != "adsb":
            self._sdrforge_view.set_tuning_range(state.tuning_range)
            self._sdrforge_view.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._sdrforge_view.set_station(
                frequency_hz=state.station.frequency_hz,
                name=state.telemetry.station_name or state.station.label,
                radio_text=state.telemetry.radio_text or state.telemetry.rds,
                stereo=state.telemetry.stereo_locked is True,
                signal=state.telemetry.signal_db,
                mode=state.station.mode_name,
            )
        signal = "--" if state.telemetry.signal_db is None else f"{state.telemetry.signal_db:.1f} dB"
        snr = "--" if state.telemetry.snr_db is None else f"{state.telemetry.snr_db:.1f} dB"
        self._signal_label.configure(text=f"SIGNAL {signal}")
        if self._receiver_controls is not None:
            mismatch = receiver_mode_mismatch(state)
            observed = state.telemetry.mode
            requested = state.station.mode_name or "--"
            mode_text = (f"MODE  {requested}  ≠  {observed}" if mismatch
                         else f"MODE  {requested}")
            self._receiver_mode_label.configure(
                text=mode_text,
                fg=self._theme.ui.accent_danger if mismatch else self._theme.ui.text,
            )
            self._receiver_signal_label.configure(text=state.scan_progress or ("SIGNAL  " + signal))
            if self._sdrforge_view is not None:
                group = self._active_group.split(":", 1)[0]
                if group in ("FM", "WEATHER"):
                    self._subcategory_strip.grid_remove()
                    self._station_info.grid()
                    name = state.telemetry.station_name.strip()
                    text = (state.telemetry.radio_text or state.telemetry.rds or "").strip()
                    if group == "FM":
                        self._info_title.configure(text="RDS  •  " + (
                            "RECEIVING" if name or text else "WAITING"))
                        self._info_name.configure(text=name or "No station ID")
                        self._info_text.configure(text=text or "Waiting for RDS data")
                    else:
                        self._info_title.configure(text="NOAA WEATHER RADIO")
                        self._info_name.configure(text=state.station.label)
                        self._info_text.configure(text="Weather broadcast • " +
                            ("Stereo" if state.telemetry.stereo_locked else "Mono"))
                else:
                    self._station_info.grid_remove()
                    self._subcategory_strip.grid()

            for button in self._live_rf_buttons:
                button.set_enabled(state.receiver_running and not state.loading and not state.error)
            starting = state.receiver_starting or self._receiver_start_pending
            self._receiver_power_button.set_text(
                "STARTING SDR…" if starting else
                ("■ STOP SDR" if state.receiver_running else "▶ START SDR"))
            self._receiver_power_button.set_enabled(not starting)
            self._receiver_power_button.set_selected(state.receiver_running)
            self._play_button.set_text("MUTE" if state.playing else "UNMUTE")
            self._play_button.set_selected(not state.playing)
            self._scan_button.set_text("STOP SCAN" if state.scanning else "SCAN BAND")
            self._scan_button.set_selected(state.scanning)
        self._snr_label.configure(text=f"SNR {snr}")
        if state.loading or state.error:
            self._launch_status.configure(text=state.error or "Loading radio…",
                                          fg=self._theme.ui.accent_danger if state.error else self._theme.ui.text)
            self._launch_status.place(relx=0.5, rely=0.5, anchor="center")
            self._launch_status.lift()
        else:
            self._launch_status.place_forget()
        if state.view == "adsb":
            if self._receiver_controls is not None:
                self._receiver_controls.grid_remove()
            self._controls.grid_remove()
            self._favorites.grid_remove()
            self._telemetry_overlay.place_forget()
        else:
            if self._receiver_controls is not None:
                self._receiver_controls.grid()
            if self._sdrforge_view is None:
                self._controls.grid()
            if self._sdrforge_view is not None:
                self._favorites.grid()
                self._telemetry_overlay.place_forget()  # Receiver header owns status.
            else:
                self._telemetry_overlay.place(relx=1.0, x=-8, y=8, anchor="ne")
        self._controls_button.configure(state=tk.DISABLED if state.view == "adsb" else tk.NORMAL)
        self._refresh_display_controls()

    def _render_favorites(self, state: RfRadioState) -> None:
        """One-touch station presets for the active radio profile."""
        ui = self._theme.ui
        profile = next((p for p in state.profiles if p.key == state.station.profile_key), None)
        signature = (profile.key, tuple((p.label, p.frequency_hz) for p in profile.presets), state.station.frequency_hz, self._preset_page) if profile else None
        if signature == self._favorites_signature:
            return
        self._favorites_signature = signature
        for child in self._favorites.winfo_children():
            child.destroy()
        if profile is None:
            return
        max_page = max(0, (len(profile.presets) - 1) // self._preset_page_size)
        self._preset_page = min(self._preset_page, max_page)
        tk.Button(
            self._favorites, text="◀", state=tk.NORMAL if self._preset_page else tk.DISABLED,
            command=lambda: self._change_preset_page(-1),
            bg=ui.control_background, fg=ui.text, relief=tk.FLAT,
            bd=0, padx=14, pady=13, font=("Sans", 11, "bold"),
        ).pack(side=tk.LEFT, padx=3)
        start = self._preset_page * self._preset_page_size
        for preset in profile.presets[start:start + self._preset_page_size]:
            tk.Button(
                self._favorites, text=preset.label,
                command=lambda p=preset, key=profile.key: self._session.request(
                    RadioRequest(RadioAction.PRESET, key=key, preset=p)),
                bg=ui.accent_primary if preset.frequency_hz == state.station.frequency_hz else ui.control_background,
                fg=ui.text, activebackground=ui.accent_primary, relief=tk.FLAT,
                bd=0, padx=10, pady=13, font=("Sans", 10, "bold"),
                highlightthickness=1, highlightbackground=ui.border,
            ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        tk.Button(
            self._favorites, text="▶",
            state=tk.NORMAL if self._preset_page < max_page else tk.DISABLED,
            command=lambda: self._change_preset_page(1),
            bg=ui.control_background, fg=ui.text, relief=tk.FLAT,
            bd=0, padx=12, pady=10,
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            self._favorites, text="☆ SAVE",
            command=lambda group=profile.group: self._add_current_preset(group),
            bg=ui.surface_alt, fg=ui.text, relief=tk.FLAT,
            bd=0, padx=12, pady=13, font=("Sans", 10, "bold"),
            highlightthickness=1, highlightbackground=ui.border,
        ).pack(side=tk.RIGHT, padx=3)

    def _change_preset_page(self, delta: int) -> None:
        profile = next((p for p in self._state.profiles
                        if p.key == self._state.station.profile_key), None)
        if profile is None:
            return
        max_page = max(0, (len(profile.presets) - 1) // self._preset_page_size)
        self._preset_page = max(0, min(max_page, self._preset_page + delta))
        self._render_favorites(self._state)

    def _schedule_telemetry_refresh(self) -> None:
        self._session.request(RadioRequest(RadioAction.REFRESH))
        self._telemetry_after_id = self.after(500, self._schedule_telemetry_refresh)

    def _on_host_resize(self, event: tk.Event) -> None:
        if self._sdrforge_view is not None:
            return
        self._session.request(RadioRequest(RadioAction.RESIZE, host=RadioHost(
            int(self._host.winfo_id()), int(self.winfo_toplevel().winfo_id()),
            max(1, event.width), max(1, event.height))))
