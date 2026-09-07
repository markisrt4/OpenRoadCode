# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""orcUi radio panel hosting and controlling external radio presentations."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import simpledialog

from apps.orcUi.adsb_control import OrcUiAdsbControl
from apps.orcUi.theme_runtime import theme_bundle
from controllers.radio.radio_profile_controller import RadioProfileController, RadioProfileState
from controllers.radio.radio_profiles import RadioProfile, RadioProfilePreset
from controllers.sdr.sdr_telemetry_monitor import SDRTelemetryMonitor
from controllers.sdr.sdr_telemetry_worker import SDRTelemetryWorker
from controllers.sdr.sdrpp_control import SDRPPControl
from frontends.x11 import X11WindowEmbedder
from ui.theme import ThemeBundle, ThemeMode

MAIN_GROUPS = (("FM", "♫ FM ▾"), ("WEATHER", "☁ WEATHER ▾"), ("AIR", "✈ AIR ▾"), ("HAM", "⌁ HAM ▾"), ("SCANNER", "⌁ SCANNER ▾"))
RADIO_GROUPS = tuple(name for name, _ in MAIN_GROUPS)


class RadioPanel(tk.Frame):
    """Automotive controls wrapped around embedded SDR++ and ADS-B views."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        embedder: X11WindowEmbedder | None = None,
        radio_control: RadioProfileController | None = None,
        sdrpp_control: SDRPPControl | None = None,
        adsb_control: OrcUiAdsbControl | None = None,
        theme: ThemeBundle | None = None,
    ) -> None:
        self._theme = theme or theme_bundle(ThemeMode.DARK)
        ui = self._theme.ui
        super().__init__(parent, bg=ui.background)
        self._embedder = embedder or X11WindowEmbedder()
        self._radio = radio_control or RadioProfileController()
        self._sdrpp = sdrpp_control or SDRPPControl()
        self._adsb = adsb_control or OrcUiAdsbControl()
        self._telemetry_worker = SDRTelemetryWorker(SDRTelemetryMonitor(self._radio))
        self._telemetry_after_id: str | None = None
        self._display = os.environ.get("DISPLAY", ":1")
        self._embedded_view = "sdrpp"
        self._active_group = "FM"
        self._group_buttons: dict[str, tk.Button] = {}
        self._drawer_open = False
        self._drawer: tk.Frame | None = None
        self._display_buttons: dict[str, tk.Button] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._groups = tk.Frame(self, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)
        self._groups.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self._build_group_bar()
        self._body = tk.Frame(self, bg=ui.background)
        self._body.grid(row=1, column=0, sticky="nsew")
        self._body.grid_columnconfigure(0, weight=1)
        self._body.grid_rowconfigure(0, weight=1)
        self._host = tk.Frame(self._body, bg=ui.background, highlightthickness=1, highlightbackground=ui.border)
        self._host.grid(row=0, column=0, sticky="nsew")
        self._host.bind("<Configure>", self._on_host_resize)

        self._telemetry_overlay = tk.Frame(self._host, bg=ui.surface_alt, highlightthickness=1, highlightbackground=ui.border)
        self._telemetry_overlay.place(relx=1.0, x=-8, y=8, anchor="ne")
        self._signal_label = tk.Label(self._telemetry_overlay, text="SIGNAL --", bg=ui.surface_alt, fg=ui.text, font=("Monospace", 8, "bold"), padx=8, pady=3)
        self._signal_label.pack(side=tk.LEFT)
        self._snr_label = tk.Label(self._telemetry_overlay, text="SNR --", bg=ui.surface_alt, fg=ui.accent_success, font=("Monospace", 8, "bold"), padx=8, pady=3)
        self._snr_label.pack(side=tk.LEFT)

        self._controls = tk.Frame(self, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)
        self._controls.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        self._controls.grid_columnconfigure(2, weight=1)
        tk.Button(self._controls, text="‹ PRESET", command=self._previous_preset, bg=ui.surface, fg=ui.text, activebackground=ui.control_background, activeforeground=ui.accent_success, relief=tk.FLAT, bd=0, padx=12, pady=7).grid(row=0, column=0, rowspan=3, sticky="ns")
        tk.Button(self._controls, text="− TUNE", command=self._tune_down, bg=ui.surface, fg=ui.text_muted, activebackground=ui.control_background, activeforeground=ui.accent_success, relief=tk.FLAT, bd=0, padx=10, pady=7).grid(row=0, column=1, rowspan=3, sticky="ns")
        center = tk.Frame(self._controls, bg=ui.surface)
        center.grid(row=0, column=2, rowspan=3, sticky="ew")
        self._station_label = tk.Label(center, text="NO PRESET", bg=ui.surface, fg=ui.text, font=("Sans", 11, "bold"))
        self._station_label.pack()
        self._frequency_label = tk.Label(center, text="--.- MHz", bg=ui.surface, fg=ui.text_muted, font=("Monospace", 9))
        self._frequency_label.pack()
        self._metadata_label = tk.Label(center, text="", bg=ui.surface, fg=ui.accent_success, font=("Sans", 8))
        self._metadata_label.pack()
        tk.Button(self._controls, text="TUNE +", command=self._tune_up, bg=ui.surface, fg=ui.text_muted, activebackground=ui.control_background, activeforeground=ui.accent_success, relief=tk.FLAT, bd=0, padx=10, pady=7).grid(row=0, column=3, rowspan=3, sticky="ns")
        tk.Button(self._controls, text="PRESET ›", command=self._next_preset, bg=ui.surface, fg=ui.text, activebackground=ui.control_background, activeforeground=ui.accent_success, relief=tk.FLAT, bd=0, padx=12, pady=7).grid(row=0, column=4, rowspan=3, sticky="ns")

        self._apply_radio_state(self._radio.state)
        self._telemetry_worker.start()
        self._schedule_telemetry_refresh()

    def destroy(self) -> None:
        if self._telemetry_after_id is not None:
            try:
                self.after_cancel(self._telemetry_after_id)
            except tk.TclError:
                pass
            self._telemetry_after_id = None
        self._telemetry_worker.stop()
        super().destroy()

    def _build_group_bar(self) -> None:
        ui = self._theme.ui
        for name, label in MAIN_GROUPS:
            command = lambda group=name: self._show_group_menu(group)
            button = tk.Button(self._groups, text=label, command=command, bg=ui.surface, fg=ui.text, activebackground=ui.control_background, activeforeground=ui.accent_success, relief=tk.FLAT, bd=0, font=("Sans", 9, "bold"), padx=9, pady=7)
            button.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._group_buttons[name] = button
        self._controls_button = tk.Button(self._groups, text="☰ CONTROLS", command=self._toggle_drawer, bg=ui.surface, fg=ui.text, activebackground=ui.control_background, activeforeground=ui.accent_success, relief=tk.FLAT, bd=0, font=("Sans", 9, "bold"), padx=12, pady=7)
        self._controls_button.pack(side=tk.RIGHT)
        self._paint_groups()

    def _show_group_menu(self, group: str) -> None:
        self._active_group = group
        self._paint_groups()
        button = self._group_buttons[group]
        ui = self._theme.ui
        menu = tk.Menu(self, tearoff=False, bg=ui.surface, fg=ui.text, activebackground=ui.control_background, activeforeground=ui.accent_success, bd=1, relief=tk.FLAT, font=("Sans", 11))
        profiles = self._radio.catalog.profiles_for_group(group)
        for profile in profiles:
            if len(profiles) == 1:
                self._add_profile_presets(menu, profile)
            else:
                submenu = tk.Menu(menu, tearoff=False, bg=ui.surface, fg=ui.text, activebackground=ui.control_background, activeforeground=ui.accent_success, font=("Sans", 11))
                self._add_profile_presets(submenu, profile)
                menu.add_cascade(label=profile.label, menu=submenu)
        if group == "AIR":
            if profiles:
                menu.add_separator()
            menu.add_command(label="✈ ADS-B Aircraft Map", command=self._show_adsb)
        if profiles:
            menu.add_separator()
            menu.add_command(label="＋ Add Current Preset", command=lambda: self._add_current_preset(group))
        self._popup_menu(menu, button)

    def _add_profile_presets(self, menu: tk.Menu, profile: RadioProfile) -> None:
        if not profile.presets:
            menu.add_command(label=profile.label, command=lambda key=profile.key: self._select_profile(key))
            return
        for preset in profile.presets:
            marker = "★ " if preset.user_defined else ""
            menu.add_command(label=f"{marker}{preset.label}", command=lambda p=profile, item=preset: self._select_preset(p, item))

    def _select_profile(self, profile_key: str) -> None:
        self._leave_adsb()
        self._run_radio_action(lambda: self._radio.select_profile(profile_key))

    def _select_preset(self, profile: RadioProfile, preset: RadioProfilePreset) -> None:
        self._leave_adsb()
        try:
            if self._radio.active_profile_key != profile.key:
                self._radio.select_profile(profile.key)
            self._apply_radio_state(self._radio.tune_preset(preset))
            self._active_group = profile.group
            self._paint_groups()
        except (OSError, RuntimeError, ValueError) as error:
            self._frequency_label.configure(text=f"RIGCTL: {error}", fg=self._theme.ui.accent_danger)

    def _add_current_preset(self, group: str) -> None:
        profiles = self._radio.catalog.profiles_for_group(group)
        if not profiles:
            return
        profile = self._radio.catalog.profile(self._radio.active_profile_key) if self._radio.active_profile_key in {p.key for p in profiles} else profiles[0]
        state = self._radio.state
        label = simpledialog.askstring("Add radio preset", "Preset name:", initialvalue=state.label, parent=self)
        if label:
            self._radio.catalog.add_user_preset(profile.key, label=label, frequency_hz=state.frequency_hz)

    def _show_adsb(self) -> None:
        ui = self._theme.ui
        self._active_group = "AIR:ADSB"
        self._paint_groups()
        self._telemetry_worker.set_include_rds(False)
        parent_window_id = int(self.winfo_toplevel().winfo_id())
        try:
            self._embedder.detach(parent_window_id)
            self.update_idletasks()
            self._adsb.configure_browser_window(position=(self._host.winfo_rootx(), self._host.winfo_rooty()), size=(max(1, self._host.winfo_width()), max(1, self._host.winfo_height())))
            self._adsb.launch(self._display)
            self.update_idletasks()
            self._embedder.embed(0, self.host_window_id, self._host.winfo_width(), self._host.winfo_height(), window_class=OrcUiAdsbControl.WINDOW_CLASS)
            self._embedded_view = "adsb"
            self._controls.grid_remove()
            self._telemetry_overlay.place_forget()
            self._controls_button.configure(state=tk.DISABLED, fg=ui.text_muted)
        except (OSError, RuntimeError, ValueError) as error:
            self._embedded_view = "none"
            self._frequency_label.configure(text=f"ADS-B: {error}", fg=ui.accent_danger)
            print(f"WARNING: ADS-B launch/embed: {type(error).__name__}: {error}")

    def _leave_adsb(self) -> None:
        if self._embedded_view != "adsb":
            return
        parent_window_id = int(self.winfo_toplevel().winfo_id())
        self._embedder.detach(parent_window_id)
        try:
            self._adsb.stop(self._display)
        except (OSError, RuntimeError, ValueError) as error:
            print(f"WARNING: ADS-B stop: {type(error).__name__}: {error}")
        self._embedded_view = "none"
        try:
            self.attach_sdrpp()
        except (OSError, RuntimeError, ValueError) as error:
            print(f"WARNING: SDR++ reattach: {type(error).__name__}: {error}")
        self._controls.grid()
        self._telemetry_overlay.place(relx=1.0, x=-8, y=8, anchor="ne")
        self._controls_button.configure(state=tk.NORMAL, fg=self._theme.ui.text)
        self._telemetry_worker.set_include_rds(self._radio.active_profile_key == "fm_radio")

    @staticmethod
    def _popup_menu(menu: tk.Menu, button: tk.Button) -> None:
        x = button.winfo_rootx()
        y = button.winfo_rooty() + button.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    @property
    def host_window_id(self) -> int:
        self.update_idletasks()
        return int(self._host.winfo_id())

    @property
    def active_group(self) -> str:
        return self._active_group

    def select_group(self, name: str) -> None:
        if name not in RADIO_GROUPS:
            raise ValueError(f"Unknown radio group: {name}")
        self._leave_adsb()
        self._active_group = name
        self._paint_groups()
        profiles = self._radio.catalog.profiles_for_group(name)
        if profiles:
            self._run_radio_action(lambda: self._radio.select_profile(profiles[0].key))

    def set_station(self, label: str, frequency_hz: int, mode_name: str | None = None) -> None:
        self._station_label.configure(text=label)
        suffix = f"   {mode_name}" if mode_name else ""
        self._frequency_label.configure(text=f"{frequency_hz / 1_000_000:.3f} MHz{suffix}", fg=self._theme.ui.text_muted)

    def attach_sdrpp(self, process_id: int = 0) -> int:
        self.update_idletasks()
        window_id = self._embedder.embed(process_id, self.host_window_id, self._host.winfo_width(), self._host.winfo_height(), window_name="SDR++")
        self._embedded_view = "sdrpp"
        return window_id

    def detach_sdrpp(self, parent_window_id: int) -> None:
        self._embedder.detach(parent_window_id)
        if self._embedded_view == "adsb":
            try:
                self._adsb.stop(self._display)
            except (OSError, RuntimeError, ValueError) as error:
                print(f"WARNING: ADS-B stop: {type(error).__name__}: {error}")
        self._embedded_view = "none"

    def clear_embedding(self) -> None:
        self._embedder.clear()

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
        self._drawer = tk.Frame(self._body, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)
        header = tk.Frame(self._drawer, bg=ui.surface_alt)
        header.pack(fill=tk.X)
        tk.Label(header, text="RADIO CONTROLS", bg=ui.surface_alt, fg=ui.text, font=("Sans", 11, "bold"), padx=12, pady=10).pack(side=tk.LEFT)
        tk.Button(header, text="✕", command=self._toggle_drawer, bg=ui.surface_alt, fg=ui.text_muted, activebackground=ui.control_background, activeforeground=ui.text, relief=tk.FLAT, bd=0, padx=12, pady=10).pack(side=tk.RIGHT)
        for key, label, action in (("waterfall", "WATERFALL", self._toggle_waterfall), ("bandplan", "BANDPLAN", self._toggle_bandplan), ("fft_hold", "PEAK HOLD", self._toggle_fft_hold)):
            button = tk.Button(self._drawer, text=label, command=action, anchor="w", bg=ui.surface, fg=ui.text_muted, activebackground=ui.control_background, activeforeground=ui.accent_success, relief=tk.FLAT, bd=0, font=("Sans", 10, "bold"), padx=16, pady=11)
            button.pack(fill=tk.X)
            self._display_buttons[key] = button
        tk.Frame(self._drawer, bg=ui.border, height=1).pack(fill=tk.X, padx=12, pady=4)
        tk.Button(self._drawer, text="AUTO RANGE", command=self._auto_range, anchor="w", bg=ui.surface, fg=ui.text, activebackground=ui.control_background, activeforeground=ui.text, relief=tk.FLAT, bd=0, padx=16, pady=11).pack(fill=tk.X)
        tk.Button(self._drawer, text="THEME…", command=self._choose_theme, anchor="w", bg=ui.surface, fg=ui.text, activebackground=ui.control_background, activeforeground=ui.text, relief=tk.FLAT, bd=0, padx=16, pady=11).pack(fill=tk.X)

    def _choose_theme(self) -> None:
        try:
            themes = self._sdrpp.themes()
        except (OSError, RuntimeError, ValueError):
            return
        if not themes:
            return
        ui = self._theme.ui
        menu = tk.Menu(self, tearoff=False, bg=ui.surface, fg=ui.text, activebackground=ui.control_background, activeforeground=ui.text)
        for theme in themes:
            menu.add_command(label=theme, command=lambda value=theme: self._sdrpp.set_theme(value))
        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()

    def _paint_toggle(self, key: str, label: str, enabled: bool) -> None:
        ui = self._theme.ui
        self._display_buttons[key].configure(text=f"{label}     {'ON' if enabled else 'OFF'}", fg=ui.accent_success if enabled else ui.text_muted, bg=ui.surface_alt if enabled else ui.surface)

    def _remote_toggle(self, key: str, label: str, action) -> None:
        try:
            self._paint_toggle(key, label, action())
        except (OSError, RuntimeError, ValueError) as error:
            self._display_buttons[key].configure(text=f"{label}     !", fg=self._theme.ui.accent_danger)
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
        for key, label, getter in (("waterfall", "WATERFALL", self._sdrpp.waterfall_visible), ("bandplan", "BANDPLAN", self._sdrpp.bandplan_visible), ("fft_hold", "PEAK HOLD", self._sdrpp.fft_hold_enabled)):
            try:
                self._paint_toggle(key, label, getter())
            except (OSError, RuntimeError, ValueError):
                self._display_buttons[key].configure(text=label, fg=ui.text_muted, bg=ui.surface)

    def _previous_preset(self) -> None:
        self._run_radio_action(self._radio.previous_preset)

    def _next_preset(self) -> None:
        self._run_radio_action(self._radio.next_preset)

    def _tune_down(self) -> None:
        self._run_radio_action(self._radio.tune_down)

    def _tune_up(self) -> None:
        self._run_radio_action(self._radio.tune_up)

    def _run_radio_action(self, action) -> None:
        self._leave_adsb()
        try:
            self._apply_radio_state(action())
        except (OSError, RuntimeError, ValueError) as error:
            self._frequency_label.configure(text=f"RIGCTL: {error}", fg=self._theme.ui.accent_danger)
            print(f"WARNING: SDR++ rigctl: {type(error).__name__}: {error}")

    def _apply_radio_state(self, state: RadioProfileState) -> None:
        self.set_station(state.label, state.frequency_hz, state.mode_name)
        include_rds = state.profile_key == "fm_radio"
        self._telemetry_worker.set_include_rds(include_rds)
        if not include_rds:
            self._metadata_label.configure(text="")

    def _schedule_telemetry_refresh(self) -> None:
        self._refresh_telemetry()
        self._telemetry_after_id = self.after(500, self._schedule_telemetry_refresh)

    def _refresh_telemetry(self) -> None:
        telemetry = self._telemetry_worker.latest
        self._signal_label.configure(text=f"SIGNAL {telemetry.signal}")
        self._snr_label.configure(text=f"SNR {telemetry.snr}")
        if self._radio.active_profile_key == "fm_radio":
            self._metadata_label.configure(text="" if telemetry.rds == "--" else telemetry.rds)
        elif self._metadata_label.cget("text"):
            self._metadata_label.configure(text="")

    def _on_host_resize(self, event: tk.Event) -> None:
        self._embedder.resize(event.width, event.height)

    def _paint_groups(self) -> None:
        ui = self._theme.ui
        parent_active = self._active_group.split(":", 1)[0]
        for name, button in self._group_buttons.items():
            active = name == parent_active
            button.configure(fg=ui.accent_success if active else ui.text, bg=ui.surface_alt if active else ui.surface)
