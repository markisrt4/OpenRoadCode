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


class RadioPanelStateMixin:
    """Apply radio snapshots and update visible receiver state."""

    def _browsed_profile(self, state: RfRadioState):
        """Prefer the tuned profile within the browsed category."""
        group = self._active_group.split(":", 1)[0]
        profiles = tuple(p for p in state.profiles if p.group == group)
        return next(
            (p for p in profiles if p.key == state.station.profile_key),
            profiles[0] if profiles else None,
        )

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
        if state.view == "adsb" and self._pending_group is None:
            self._active_group = "AIR:ADSB"
        elif profile is not None:
            if self._pending_group is None or (
                self._sdrforge_view is None and profile.group == self._pending_group
            ):
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
                bandwidth_hz=(state.telemetry.bandwidth_hz
                              if state.receiver_running and not receiver_mode_mismatch(state)
                              and state.telemetry.frequency_hz == state.station.frequency_hz
                              else None),
                observed_mode=state.telemetry.mode if receiver_mode_mismatch(state) else None,
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
                if not self._scan_dismissed and (self._scan_requested or state.scanning or state.scan_hits):
                    self._station_info.grid_remove()
                    self._subcategory_strip.grid_remove()
                    self._scan_card.place(relx=1.0, rely=0, relheight=1.0,
                                          width=320, anchor="ne")
                    self._scan_card.lift()
                    self._scan_status.configure(text=(
                        state.scan_progress if state.scanning and state.scan_progress else
                        "Scanning…" if state.scanning else
                        f"{len(state.scan_hits)} stations found"))
                    signature = (state.scan_hits, state.presets_writable)
                    if signature != self._scan_signature or not state.scanning and not state.scan_hits:
                        self._scan_signature = signature
                        self._render_scan_results()
                elif group in ("FM", "WEATHER"):
                    self._scan_card.place_forget()
                    self._subcategory_strip.grid_remove()
                    self._station_info.grid()
                    name = state.telemetry.station_name.strip()
                    text = (state.telemetry.radio_text or state.telemetry.rds or "").strip()
                    if profile is None or profile.group != group:
                        self._info_title.configure(text=group)
                        self._info_name.configure(text="Select a preset to tune")
                        self._info_text.configure(text="Current receiver remains active")
                    elif group == "FM":
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
                    self._scan_card.place_forget()
                    self._station_info.grid_remove()
                    self._subcategory_strip.grid()

            for button in self._live_rf_buttons:
                button.set_enabled(state.receiver_running and not state.loading and not state.error)
            starting = state.receiver_starting or self._receiver_start_pending
            if self._sdrforge_view is not None:
                if starting or state.receiver_running:
                    self._spectrum_start_button.place_forget()
                else:
                    self._spectrum_start_button.place(relx=0.5, rely=0.68, anchor="center")
                    self._spectrum_start_button.tk.call("raise", self._spectrum_start_button._w)
            self._receiver_power_button.set_text(
                "STARTING SDR…" if starting else
                ("■ STOP SDR" if state.receiver_running else "▶ START SDR"))
            unavailable = state.error.startswith("SDRForge service unavailable:")
            self._receiver_power_button.set_enabled(not starting and not unavailable)
            if self._sdrforge_view is not None:
                self._spectrum_start_button.configure(state="disabled" if unavailable else "normal")
                color = self._theme.ui.border if unavailable else self._theme.ui.accent_primary
                self._spectrum_start_button.itemconfigure(1, outline=color)
                self._spectrum_start_button.itemconfigure(2, fill=color)
            self._receiver_power_button.set_selected(state.receiver_running)
            self._play_button.set_text("MUTE" if state.playing else "UNMUTE")
            self._play_button.set_selected(not state.playing)
            self._scan_button.set_text("STOP SCAN" if state.scanning else "SCAN BAND")
            self._scan_button.set_selected(state.scanning)
        self._snr_label.configure(text=f"SNR {snr}")
        if state.loading or state.error:
            self._launch_status.configure(text=state.error or "Loading radio…",
                                          fg=self._theme.ui.accent_danger if state.error else self._theme.ui.text)
            self._launch_status.configure(wraplength=max(120, self._host.winfo_width() - 40))
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

