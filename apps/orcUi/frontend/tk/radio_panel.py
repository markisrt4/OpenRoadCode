# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""orcUi radio panel hosting and controlling external radio presentations."""

from __future__ import annotations

import os
from collections.abc import Callable
import tkinter as tk

from apps.orcUi.adapters.adsb_control import OrcUiAdsbControl
from apps.orcUi.theme_runtime import theme_bundle
from controllers.radio.radio_profile_controller import RadioProfileController, RadioProfileState
from controllers.sdr.sdr_telemetry_monitor import SDRTelemetryMonitor
from controllers.sdr.sdr_telemetry_worker import SDRTelemetryWorker
from controllers.sdr.sdrpp_control import SDRPPControl
from frontends.x11 import X11WindowEmbedder
from ui.theme import ThemeBundle, ThemeMode
from .shell_metrics import FONT_BODY, FONT_CONTROL, FONT_SMALL
from .radio_display_controls import RadioDisplayControlsMixin
from .radio_group_menu import MAIN_GROUPS, RadioGroupMenuMixin

MAIN_GROUPS = (
    ("FM", "♫ FM ▾"),
    ("WEATHER", "☁ WEATHER ▾"),
    ("AIR", "✈ AIR ▾"),
    ("HAM", "⌁ HAM ▾"),
    ("SCANNER", "⌁ SCANNER ▾"),
)
RADIO_GROUPS = tuple(name for name, _ in MAIN_GROUPS)


class RadioPanel(RadioGroupMenuMixin, RadioDisplayControlsMixin, tk.Frame):
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
        rf_active: Callable[[], bool] | None = None,
        release_rf: Callable[[], None] | None = None,
    ) -> None:
        self._theme = theme or theme_bundle(ThemeMode.DARK)
        ui = self._theme.ui
        super().__init__(parent, bg=ui.background)
        self._embedder = embedder or X11WindowEmbedder()
        self._radio = radio_control or RadioProfileController()
        self._sdrpp = sdrpp_control or SDRPPControl()
        self._adsb = adsb_control or OrcUiAdsbControl()
        self._rf_active = rf_active or (lambda: False)
        self._release_rf = release_rf or (lambda: None)
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







    def show_adsb(self) -> None:
        """Present ADS-B without allowing it to preempt an active RF receiver."""
        self._show_adsb()

    def _show_adsb(self) -> None:
        ui = self._theme.ui
        scheme = "light" if self._theme == theme_bundle(ThemeMode.LIGHT) else "dark"
        self._active_group = "AIR:ADSB"
        self._paint_groups()
        self._telemetry_worker.set_include_rds(False)
        parent_window_id = int(self.winfo_toplevel().winfo_id())
        try:
            if self._rf_active():
                self._release_rf()
            self._adsb.assert_available()
            self._adsb.set_preferred_color_scheme(scheme)
            self._embedder.detach(parent_window_id)
            self.update_idletasks()
            self._adsb.configure_browser_window(
                position=(self._host.winfo_rootx(), self._host.winfo_rooty()),
                size=(max(1, self._host.winfo_width()), max(1, self._host.winfo_height())),
            )
            self._adsb.launch(self._display)
            self.update_idletasks()
            self._embedder.embed(
                0,
                self.host_window_id,
                self._host.winfo_width(),
                self._host.winfo_height(),
                window_class=OrcUiAdsbControl.WINDOW_CLASS,
            )
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
        self._frequency_label.configure(
            text=f"{frequency_hz / 1_000_000:.3f} MHz{suffix}", fg=self._theme.ui.text_muted
        )

    def attach_sdrpp(self, process_id: int = 0) -> int:
        self.update_idletasks()
        window_id = self._embedder.embed(
            process_id,
            self.host_window_id,
            self._host.winfo_width(),
            self._host.winfo_height(),
            window_name="SDR++",
            window_class="sdrpp",
            relax_size_hints=True,
        )
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
            self._frequency_label.configure(
                text=f"RIGCTL: {error}", fg=self._theme.ui.accent_danger
            )
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
