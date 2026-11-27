# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""orcUi radio panel hosting and controlling external radio presentations."""

from __future__ import annotations

import tkinter as tk
from functools import partial

from ui.radio.radio_profile_state import RadioProfileState
from ui.radio.radio_visualization_config import RadioVisualizationConfig
from ui.radio.rf_radio_if import (
    RadioAction,
    RadioHost,
    RadioRequest,
    RfRadioSession,
    RfRadioState,
    receiver_mode_mismatch,
)
from ui.radio.sdrforge_spectrum_if import SpectrumPresentation
from ui.theme import ThemeBundle

from .automotive_radio_button import AutomotiveRadioButton
from .radio_display_controls import RadioDisplayControlsMixin
from .radio_group_menu import MAIN_GROUPS, RadioGroupMenuMixin
from .radio_panel_layout_mixin import RadioPanelLayoutMixin
from .radio_panel_state_mixin import RadioPanelStateMixin
from .radio_scan_mixin import RadioScanMixin
from .radio_tuning_gestures_mixin import RadioTuningGesturesMixin

RADIO_GROUPS = tuple(name for name, _ in MAIN_GROUPS)


def receiver_sidebar_width(panel_width: int) -> int:
    """Reserve room for the FFT while scaling the controls on smaller windows."""
    return max(240, min(320, panel_width // 4))


class RadioPanel(
    RadioScanMixin,
    RadioTuningGesturesMixin,
    RadioPanelStateMixin,
    RadioPanelLayoutMixin,
    RadioGroupMenuMixin,
    RadioDisplayControlsMixin,
):
    """Automotive controls for native RF and embedded ADS-B views."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        session: RfRadioSession,
        theme: ThemeBundle,
        native_sdrforge: bool = False,
        visualization: RadioVisualizationConfig | None = None,
        fm_only: bool = False,
    ) -> None:
        self._theme = theme
        self._driving_radio = native_sdrforge
        self._fm_only = fm_only
        self._plots_visible = not fm_only
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
        self._favorites_signature: (
            tuple[str, tuple[tuple[str, int], ...], str, int, int, bool] | None
        ) = None
        self._preset_page = 0
        self._preset_page_size = 4
        self._scan_selected: set[int] = set()
        self._scan_signature: tuple[tuple[int, ...], bool] | None = None
        self._scan_drag_y: int | None = None
        self._scan_dragged = False
        self._scan_dismissed = False
        self._scan_requested = False

        self._build_radio_layout(
            ui=ui, native_sdrforge=native_sdrforge, theme=theme, visualization=visualization
        )

    def _resize_receiver_sidebar(self, event: tk.Event[tk.Misc]) -> None:
        """Keep the waterfall dominant as the radio panel is resized."""
        if event.widget is not self or self._receiver_controls is None or not self._plots_visible:
            return
        width = receiver_sidebar_width(event.width)
        if self._receiver_controls.winfo_reqwidth() != width:
            self._receiver_controls.configure(width=width)
            self._body.grid_columnconfigure(1, minsize=width)
            self._info_text.configure(wraplength=max(180, width - 32))

    def _poll_sdrforge_spectrum(self) -> None:
        self._sdrforge_after_id = None
        if self._sdrforge_view is not None and self._plots_visible:
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
            self._plot_toggle.set_palette(
                background=ui.control_background,
                accent=ui.accent_primary,
                foreground=ui.text,
                border=ui.border,
            )
        self._favorites.configure(bg=ui.surface)
        self._subcategory_strip.configure(bg=ui.surface)
        if self._receiver_controls is not None:
            for child in self._receiver_controls.winfo_children():
                if isinstance(child, AutomotiveRadioButton):
                    child.set_palette(
                        background=ui.control_background,
                        accent=ui.accent_primary,
                        foreground=ui.text,
                        border=ui.border,
                    )
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
                fg=ui.accent_danger if receiver_mode_mismatch(self._state) else ui.text_muted,
            )
        if self._sdrforge_view is not None:
            self._sdrforge_view.set_theme_bundle(theme)

    def _render_subcategory_tiles(self, state: RfRadioState) -> None:
        """One-touch subcategory selection, with no popup or nested menus."""
        group = self._active_group.split(":", 1)[0]
        profiles = tuple(p for p in state.profiles if p.group == group)
        signature = (group, tuple((p.key, p.label) for p in profiles), state.station.profile_key)
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
                self._subcategory_strip,
                text=profile.label,
                command=partial(
                    self._session.request, RadioRequest(RadioAction.PROFILE, key=profile.key)
                ),
                selected=selected,
                height=40,
                background=ui.control_background,
                accent=ui.accent_primary,
                foreground=ui.text,
                border=ui.border,
            ).grid(row=row, column=col, sticky="nsew", padx=2, pady=1)
            self._subcategory_strip.grid_columnconfigure(col, weight=1, uniform="profiles")
        if group == "AIR":
            row, col = divmod(len(profiles), 2)
            AutomotiveRadioButton(
                self._subcategory_strip,
                text="ADS-B MAP",
                command=self._show_adsb,
                selected=self._active_group == "AIR:ADSB",
                height=40,
                background=ui.control_background,
                accent=ui.accent_primary,
                foreground=ui.text,
                border=ui.border,
            ).grid(row=row, column=col, sticky="nsew", padx=2, pady=1)
            self._subcategory_strip.grid_columnconfigure(col, weight=1, uniform="profiles")

    def _native_host(self) -> RadioHost:
        self.update_idletasks()
        return RadioHost(
            int(self._host.winfo_id()),
            int(self.winfo_toplevel().winfo_id()),
            max(1, self._host.winfo_width()),
            max(1, self._host.winfo_height()),
            self._host.winfo_rootx(),
            self._host.winfo_rooty(),
        )

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
        self._session.request(
            RadioRequest(
                RadioAction.ADSB,
                host=self._native_host(),
                color_scheme="light"
                if sum(self.winfo_rgb(self._theme.ui.background)) > 3 * 32767
                else "dark",
            )
        )

    @property
    def active_group(self) -> str:
        return self._active_group

    def select_group(self, name: str) -> None:
        if name not in RADIO_GROUPS:
            raise ValueError(f"Unknown radio group: {name}")
        self._active_group = name
        self._pending_group = name
        self._scan_dismissed = True
        self._scan_requested = False
        self._subcategory_signature = None
        self._favorites_signature = None
        self._paint_groups()
        if self._sdrforge_view is not None:
            self._render_subcategory_tiles(self._state)
            if self._state.view != "adsb":
                self._preset_page = 0
                self._render_favorites(self._state)
                self._show_radio_info()
        profiles = tuple(p for p in self._state.profiles if p.group == name)
        if name == "AIR" and not profiles:
            self._show_adsb()
        elif profiles:
            profile = next(
                (p for p in profiles if p.key == self._state.station.profile_key), profiles[0]
            )
            if profile.key != self._state.station.profile_key or self._state.view == "adsb":
                self._session.request(RadioRequest(RadioAction.PROFILE, key=profile.key))
            else:
                self._pending_group = None

    def set_station(self, label: str, frequency_hz: int, mode_name: str | None = None) -> None:
        self._station_label.configure(text=label)
        suffix = f"   {mode_name}" if mode_name else ""
        self._frequency_label.configure(
            text=f"{frequency_hz / 1_000_000:.3f} MHz{suffix}", fg=self._theme.ui.text_muted
        )

    def deactivate(self) -> None:
        self._session.deactivate()
        if self._telemetry_after_id is not None:
            self.after_cancel(self._telemetry_after_id)
            self._telemetry_after_id = None

    def detach_native_client(self, parent_window_id: int) -> None:
        self.deactivate()

    def _toggle_receiver_power(self) -> None:
        if self._receiver_start_pending or self._state.receiver_starting:
            return
        if not self._state.receiver_running:
            self._receiver_start_pending = True
            if self._sdrforge_view is not None:
                self._spectrum_start_button.place_forget()
            self._receiver_power_button.set_text("STARTING SDR…")
            self._receiver_power_button.set_enabled(False)
        action = (
            RadioAction.STOP_RECEIVER
            if self._state.receiver_running
            else RadioAction.START_RECEIVER
        )
        self._session.request(RadioRequest(action))

    def _toggle_play(self) -> None:
        if self._sdrforge_view is not None and not self._state.receiver_running:
            return
        action = RadioAction.PAUSE if self._state.playing else RadioAction.PLAY
        self._session.request(RadioRequest(action))

    def auto_range_spectrum(self) -> None:
        """Reset native spectrum scaling locally."""
        if self._sdrforge_view is not None:
            self._sdrforge_view.auto_range()

    def _render_favorites(self, state: RfRadioState) -> None:
        """One-touch station presets for the active radio profile."""
        ui = self._theme.ui
        profile = self._browsed_profile(state)
        signature = (
            (
                profile.key,
                tuple((p.label, p.frequency_hz) for p in profile.presets),
                state.station.profile_key,
                state.station.frequency_hz,
                self._preset_page,
                state.presets_writable,
            )
            if profile
            else None
        )
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
            self._favorites,
            text="◀",
            state=tk.NORMAL if self._preset_page else tk.DISABLED,
            command=lambda: self._change_preset_page(-1),
            bg=ui.control_background,
            fg=ui.text,
            relief=tk.FLAT,
            bd=0,
            padx=14,
            pady=13,
            font=("Sans", 11, "bold"),
        ).pack(side=tk.LEFT, padx=3)
        start = self._preset_page * self._preset_page_size
        for preset in profile.presets[start : start + self._preset_page_size]:
            tk.Button(
                self._favorites,
                text=preset.label,
                command=partial(
                    self._session.request,
                    RadioRequest(RadioAction.PRESET, key=profile.key, preset=preset),
                ),
                bg=ui.accent_primary
                if profile.key == state.station.profile_key
                and preset.frequency_hz == state.station.frequency_hz
                else ui.control_background,
                fg=ui.text,
                activebackground=ui.accent_primary,
                relief=tk.FLAT,
                bd=0,
                padx=10,
                pady=13,
                font=("Sans", 10, "bold"),
                highlightthickness=1,
                highlightbackground=ui.border,
            ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        tk.Button(
            self._favorites,
            text="▶",
            state=tk.NORMAL if self._preset_page < max_page else tk.DISABLED,
            command=lambda: self._change_preset_page(1),
            bg=ui.control_background,
            fg=ui.text,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=10,
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            self._favorites,
            text="☆ SAVE",
            command=partial(self._add_current_preset, profile.group),
            state=tk.NORMAL
            if profile.key == state.station.profile_key and state.presets_writable
            else tk.DISABLED,
            bg=ui.surface_alt,
            fg=ui.text,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=13,
            font=("Sans", 10, "bold"),
            highlightthickness=1,
            highlightbackground=ui.border,
        ).pack(side=tk.RIGHT, padx=3)

    def _change_preset_page(self, delta: int) -> None:
        profile = self._browsed_profile(self._state)
        if profile is None:
            return
        max_page = max(0, (len(profile.presets) - 1) // self._preset_page_size)
        self._preset_page = max(0, min(max_page, self._preset_page + delta))
        self._render_favorites(self._state)

    def _schedule_telemetry_refresh(self) -> None:
        self._session.request(RadioRequest(RadioAction.REFRESH))
        self._telemetry_after_id = self.after(500, self._schedule_telemetry_refresh)

    def _on_host_resize(self, event: tk.Event[tk.Misc]) -> None:
        if self._sdrforge_view is not None:
            return
        self._session.request(
            RadioRequest(
                RadioAction.RESIZE,
                host=RadioHost(
                    int(self._host.winfo_id()),
                    int(self.winfo_toplevel().winfo_id()),
                    max(1, event.width),
                    max(1, event.height),
                ),
            )
        )
