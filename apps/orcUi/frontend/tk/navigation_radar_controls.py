# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Weather-radar controls shared with the navigation panel."""

import tkinter as tk

from controllers.weather.radar_palette import RadarPalette
from .shell_metrics import FONT_CONTROL
from .radar_replay_panel import RadarReplayPanel


class NavigationRadarControls:
    """Build radar widgets and handle frame, palette, and visibility controls."""

    def _build_radar_controls(self, bar: tk.Frame) -> None:
        ui = self._theme_bundle.ui
        self._radar_button = None
        if self._on_radar_toggle is None:
            return
        self._radar_replay_panel = None
        self._radar_loading = False
        self._radar_button = tk.Button(
            bar, text="☰ RADAR", bg=ui.control_background, fg=ui.text,
            activebackground=ui.control_active, activeforeground=ui.control_text,
            relief=tk.FLAT, font=("Sans", FONT_CONTROL, "bold"), padx=8, pady=4,
            command=self._toggle_radar_menu,
        )
        self._classic_radar_var = tk.BooleanVar(value=self._radar_palette is RadarPalette.CLASSIC)
        self._radar_quick_toggle = tk.Button(
            bar, text="☁", command=self._toggle_radar,
            bg=ui.control_background, activebackground=ui.control_active,
            activeforeground=ui.control_text, relief=tk.FLAT,
            font=("Sans", FONT_CONTROL + 5, "bold"), padx=6, pady=0,
        )
        # RIGHT packs the first widget at the outer edge: cloud, then menu.
        self._radar_quick_toggle.pack(side=tk.RIGHT, padx=(4, 0), pady=3)
        self._radar_button.pack(side=tk.RIGHT, padx=(4, 0), pady=3)
        self._render_radar_state()

    def _toggle_radar_menu(self) -> None:
        if self._radar_replay_panel is not None:
            self.close_radar_menu()
            return
        close_weather = self.__dict__.get("_close_weather_menu")
        if close_weather is not None:
            close_weather()
        self._radar_replay_panel = RadarReplayPanel(
            self, self._radar_button,
            on_play=self._on_radar_play, on_seek=self._on_radar_seek,
            on_live=self._on_radar_live, on_close=self.close_radar_menu,
            on_palette=self._set_classic_palette,
            classic=self._radar_palette is RadarPalette.CLASSIC,
            on_speed=self._set_radar_speed, speed_value=self._radar_speed,
            ui=self._theme_bundle.ui,
            on_source=self._on_radar_source,
        )
        self._render_radar_state()

    def close_radar_menu(self) -> None:
        """Dismiss the timeline without changing radar visibility."""
        popup = getattr(self, "_radar_replay_panel", None)
        if popup is not None:
            popup.destroy()
            self._radar_replay_panel = None

    def _set_classic_palette(self, classic: bool) -> None:
        self._classic_radar_var.set(classic)
        self._toggle_radar_palette()

    def _set_radar_speed(self, speed: float) -> None:
        self._radar_speed = speed
        if self._on_radar_speed is not None:
            self._on_radar_speed(speed)

    def set_radar_timeline(self, times, index, playing: bool = False, forecast: bool = False) -> None:
        """Update the timeline and its playback state from the radar controller."""
        self._radar_times = times
        self._radar_index = index
        self._radar_playing = playing
        self._radar_forecast = forecast
        self._render_radar_state()

    def set_radar_loading(self, loading: bool) -> None:
        """Show when playback is waiting for forecast tiles."""
        self._radar_loading = loading
        self._render_radar_state()

    def _toggle_radar(self) -> None:
        self._radar_enabled = not self._radar_enabled
        self._render_radar_state()
        if self._on_radar_toggle is not None:
            self._on_radar_toggle(self._radar_enabled)

    def _toggle_radar_palette(self) -> None:
        self._radar_palette = (
            RadarPalette.CLASSIC if self._classic_radar_var.get()
            else RadarPalette.UNIVERSAL
        )
        if self._on_radar_palette_changed is not None:
            self._on_radar_palette_changed(self._radar_palette)

    def set_radar_frame_time(self, frame_time: int | None) -> None:
        """Show the timestamp of the radar frame currently on the map."""
        self._radar_frame_time = frame_time
        self._render_radar_state()

    def _render_radar_state(self) -> None:
        if self._radar_button is None:
            return
        ui = self._theme_bundle.ui
        if hasattr(self, "_radar_visible_var"):
            self._radar_visible_var.set(self._radar_enabled)
        self._radar_button.configure(
            text="☰ RADAR ●" if self._radar_enabled else "☰ RADAR",
            fg=ui.accent_success if self._radar_enabled else ui.text,
        )

        if hasattr(self, "_radar_quick_toggle"):
            self._radar_quick_toggle.configure(
                fg=ui.accent_success if self._radar_enabled else ui.text_muted,
                relief=tk.SUNKEN if self._radar_enabled else tk.FLAT,
            )
        popup = getattr(self, "_radar_replay_panel", None)
        if popup is not None:
            popup.render(self._radar_times, self._radar_index,
                         enabled=self._radar_enabled, playing=self._radar_playing,
                         forecast=self._radar_forecast, loading=self._radar_loading)

        callback = self.__dict__.get("_on_weather_visibility_changed")
        if callback is not None:
            callback()

    def _radar_button_text(self) -> str:
        if not self._radar_enabled:
            return "RADAR"
        if self._radar_frame_time is None:
            return "RADAR • …"

        from datetime import datetime

        frame = datetime.fromtimestamp(self._radar_frame_time).astimezone()
        return f"RADAR • {frame.strftime('%-I:%M %p')}"
