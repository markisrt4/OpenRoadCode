# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Native SDRForge spectrum, waterfall, and listener-facing station presentation.

This widget owns no SDR hardware. Composition supplies immutable snapshots and
spectrum bins, keeping transport and DSP outside Tk's UI thread.
"""
from __future__ import annotations

import tkinter as tk
from dataclasses import replace
import re
from time import monotonic

from ui.radio.radio_visualization_config import (RadioRenderer, RadioVisualizationConfig, select_renderer,
    load_rf_visualization_settings, save_rf_visualization_settings)
from collections import deque
from collections.abc import Sequence

from ui.radio.sdrforge_spectrum_if import SpectrumViewport
from ui.theme import ThemeBundle
from .opengl_radio_surface import OpenGLRadioSurface, available as opengl_available


class SdrForgeReceiverView(tk.Frame):
    """Responsive native receiver visualization for the ORC radio panel."""

    def __init__(self, parent: tk.Misc, *, theme: ThemeBundle,
                 visualization: RadioVisualizationConfig | None = None) -> None:
        super().__init__(parent, bg=theme.ui.background)
        self._theme = theme
        self._visualization = visualization or RadioVisualizationConfig()
        overrides = load_rf_visualization_settings()
        try:
            self._visualization = replace(
                self._visualization,
                renderer=RadioRenderer(str(overrides.get("renderer", self._visualization.renderer.value))),
                max_fps=int(overrides.get("max_fps", self._visualization.max_fps)),
                waterfall_rows=int(overrides.get("waterfall_rows", self._visualization.waterfall_rows)),
                palette=str(overrides.get("palette", self._visualization.palette)),
            )
        except (TypeError, ValueError):
            pass
        self._renderer = select_renderer(self._visualization, opengl_available=opengl_available())
        self._gl_surface = None
        self._last_spectrum_draw = 0.0
        self._draw_pending = False
        self._bins: tuple[float, ...] = ()
        self._peak_bins: tuple[float, ...] = ()
        self._waterfall_enabled = True
        self._peak_hold_enabled = False
        self._center_frequency_hz: int | None = None
        self._sample_rate_hz: int | None = None
        self._viewport: SpectrumViewport | None = None
        self._recenter_on_tune = overrides.get("recenter_on_tune", True) is not False
        self._db_floor: float | None = None
        self._db_ceiling: float | None = None
        self._history: deque[tuple[float, ...]] = deque(maxlen=self._visualization.waterfall_rows)
        self._station = "--"
        self._mode = ""
        self._frequency_hz = 0
        self._radio_text = ""
        self._stereo = False
        self._signal: float | None = None
        self._presets: tuple[tuple[str, int], ...] = ()
        self._on_tune = None
        self._on_spectrum_tune = None
        self._tune_range: tuple[int, int, int] | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._canvas = tk.Canvas(self, bg=theme.ui.background, bd=0, highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._canvas.bind("<Configure>", lambda _event: self._schedule_render())
        self._canvas.bind("<Button-1>", self._handle_spectrum_click)
        if self._renderer is RadioRenderer.OPENGL:
            self._gl_surface = OpenGLRadioSurface(self, width=320, height=180)
            self._gl_surface.place(x=0, y=80, relwidth=1, height=180)
            self._gl_surface.bind("<Button-1>", self._handle_spectrum_click)
        # Keep spectrum navigation in its own band, away from the MHz heading.
        self._spectrum_toolbar_visible = True
        self._spectrum_controls = tk.Frame(self, bg=theme.ui.surface)
        self._spectrum_buttons = []
        for label, callback in (
            ("◀", lambda: self.pan_spectrum(-0.20)),
            ("−", lambda: self.zoom_spectrum(1.5)),
            ("+", lambda: self.zoom_spectrum(1 / 1.5)),
            ("▶", lambda: self.pan_spectrum(0.20)),
        ):
            button = tk.Button(
                self._spectrum_controls, text=label, command=callback,
                bg=theme.ui.control_background, fg=theme.ui.text,
                relief=tk.FLAT, bd=0, width=3, padx=2, pady=3,
                font=("Sans", 10, "bold"))
            button.pack(side="left", padx=2)
            self._spectrum_buttons.append(button)
        self._recenter_button = tk.Button(
            self._spectrum_controls, command=self._toggle_recenter,
            bg=theme.ui.control_background, fg=theme.ui.text,
            relief=tk.FLAT, bd=0, padx=6, pady=3, font=("Sans", 9, "bold"))
        self._recenter_button.pack(side="left", padx=(4, 2))
        self._update_recenter_button()
        # Secondary status belongs with the spectrum tools, not the MHz heading.
        self._mode_label = tk.Label(
            self, text="", bg=theme.ui.surface,
            fg=theme.ui.text_muted, font=("Sans", 9))
        # Place independently so the label aligns with the right edge of the FFT.
        self._toolbar_toggle = tk.Button(
            self, text="HIDE ◀", command=self._toggle_spectrum_toolbar,
            bg=theme.ui.control_background, fg=theme.ui.text,
            relief=tk.FLAT, bd=0, padx=6, pady=3,
            font=("Sans", 9, "bold"))
        # Preset navigation belongs to RadioPanel, not inside the spectrum.

    def _toggle_spectrum_toolbar(self) -> None:
        """Toggle controls without hiding the button that restores them."""
        self._spectrum_toolbar_visible = not self._spectrum_toolbar_visible
        self._schedule_render()

    def _update_recenter_button(self) -> None:
        self._recenter_button.configure(
            text="CENTER ●" if self._recenter_on_tune else "CENTER ○",
            fg=self._theme.ui.accent_primary if self._recenter_on_tune else self._theme.ui.text)

    def _toggle_recenter(self) -> None:
        self.set_recenter_on_tune(not self._recenter_on_tune)

    def set_recenter_on_tune(self, enabled: bool) -> None:
        self._recenter_on_tune = bool(enabled)
        if self._viewport is not None:
            self._viewport = replace(self._viewport, recenter_on_tune=bool(enabled))
            if enabled and self._frequency_hz:
                self._viewport = replace(self._viewport, center_hz=float(self._frequency_hz))
            self._constrain_viewport()
        settings = load_rf_visualization_settings()
        settings["recenter_on_tune"] = bool(enabled)
        save_rf_visualization_settings(settings)
        self._update_recenter_button()
        self._schedule_render()

    def _constrain_viewport(self) -> None:
        """Keep the visible FFT window inside the actual sampled RF band."""
        viewport = self._viewport
        if viewport is None or self._center_frequency_hz is None or not self._sample_rate_hz:
            return
        rate = float(self._sample_rate_hz)
        span = min(viewport.span_hz, rate)
        margin = (rate - span) / 2
        center = max(self._center_frequency_hz - margin,
                     min(self._center_frequency_hz + margin, viewport.center_hz))
        self._viewport = replace(viewport, center_hz=center, span_hz=span)

    def pan_spectrum(self, fraction: float) -> None:
        if self._viewport is not None:
            self._recenter_on_tune = False
            self._update_recenter_button()
            self._viewport = replace(self._viewport.pan(fraction), recenter_on_tune=False)
            self._constrain_viewport()
            self._schedule_render()

    def zoom_spectrum(self, factor: float) -> None:
        if self._viewport is not None:
            self._viewport = self._viewport.zoom(
                factor, max_span_hz=float(self._sample_rate_hz or self._viewport.span_hz))
            self._constrain_viewport()
            self._schedule_render()

    def _viewport_row(self, row: Sequence[float]) -> tuple[float, ...]:
        """Project source FFT values into the visible frequency window."""
        viewport = self._viewport
        if not row or viewport is None or not self._center_frequency_hz or not self._sample_rate_hz:
            return tuple(row)
        source_start = self._center_frequency_hz - self._sample_rate_hz / 2
        scale = len(row) / self._sample_rate_hz
        length = min(len(row), 512)
        return tuple(
            row[index] if 0 <= index < len(row) else 0.0
            for index in (
                round((viewport.frequency_at(i / max(1, length - 1)) - source_start) * scale)
                for i in range(length)
            )
        )

    def set_spectrum_tune_handler(self, handler) -> None:
        """Receive frequency selections without coupling the widget to radio control."""
        self._on_spectrum_tune = handler

    def set_tuning_range(self, tuning_range: tuple[int, int, int] | None) -> None:
        """Use the active profile's band limits and tuning step."""
        self._tune_range = tuning_range

    def _handle_spectrum_click(self, event) -> None:
        if not self._on_spectrum_tune or not self._center_frequency_hz or not self._sample_rate_hz:
            return
        # The header, controls and station footer are not tuning targets.
        if event.widget is self._canvas:
            h = self._canvas.winfo_height()
            header = 54 if h < 260 else 80
            if event.y < header + 34 + 22:
                return
            footer = (24 if h < 260 else 32) if self._radio_text and (self._mode in ("WFM", "FM") or 76_000_000 <= self._frequency_hz <= 108_000_000) else 0
            if event.y >= h - footer:
                return
        width = max(1, event.widget.winfo_width())
        position = max(0.0, min(1.0, event.x / width))
        hz = (self._viewport.frequency_at(position) if self._viewport is not None
              else self._center_frequency_hz + (position - 0.5) * self._sample_rate_hz)
        if self._tune_range is None:
            return
        low, high, step = self._tune_range
        if step <= 0 or high < low or not low <= hz <= high:
            return
        snapped = low + round((hz - low) / step) * step
        if low <= snapped <= high:
            self._recenter_on_tune = False
            if self._viewport is not None:
                self._viewport = replace(self._viewport, recenter_on_tune=False)
            self._update_recenter_button()
            self._on_spectrum_tune(int(snapped))
            self._schedule_render()

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        self._theme = theme
        self.configure(bg=theme.ui.background)
        self._canvas.configure(bg=theme.ui.background)
        self._spectrum_controls.configure(bg=theme.ui.surface)
        for button in (*self._spectrum_buttons, self._recenter_button, self._toolbar_toggle):
            button.configure(bg=theme.ui.control_background, fg=theme.ui.text)
        self._update_recenter_button()
        self._schedule_render()

    def set_station(self, *, frequency_hz: int, name: str = "",
                    radio_text: str = "", stereo: bool = False,
                    signal: float | None = None, mode: str = "") -> None:
        presentation = (frequency_hz, name, radio_text, stereo, signal, mode)
        if getattr(self, "_last_presentation", None) == presentation:
            return
        self._last_presentation = presentation
        self._mode = mode.upper()
        self._frequency_hz = frequency_hz
        self._station = name or "--"
        self._radio_text = radio_text if (self._mode in ("WFM", "FM") or 76_000_000 <= frequency_hz <= 108_000_000) else ""
        self._stereo = stereo
        self._signal = signal
        if self._recenter_on_tune and self._viewport is not None and frequency_hz:
            self._viewport = replace(self._viewport, center_hz=float(frequency_hz))
            self._constrain_viewport()
        self._schedule_render()

    def set_display_controls(self, *, waterfall: bool, peak_hold: bool) -> None:
        """Apply native radio display preferences to the actual renderer."""
        waterfall = bool(waterfall)
        peak_hold = bool(peak_hold)
        if self._waterfall_enabled == waterfall and self._peak_hold_enabled == peak_hold:
            return
        self._waterfall_enabled = waterfall
        if peak_hold and not self._peak_hold_enabled:
            self._peak_bins = self._bins
        self._peak_hold_enabled = peak_hold
        self._schedule_render()

    def auto_range(self) -> None:
        """Discard the previous dB range and recompute it on the next FFT."""
        self._db_floor = None
        self._db_ceiling = None
        self._schedule_render()

    def clear_spectrum(self) -> None:
        """Discard stale FFT, peak hold, and waterfall after receiver stop."""
        self._bins = ()
        self._peak_bins = ()
        self._history.clear()
        self._db_floor = None
        self._db_ceiling = None
        self._center_frequency_hz = None
        self._sample_rate_hz = None
        self._viewport = None
        if self._gl_surface is not None:
            self._gl_surface.update_data((), (), self._visualization.palette)
        self._schedule_render()

    def set_spectrum(self, bins: Sequence[float], *,
                     center_frequency_hz: int | None = None,
                     sample_rate_hz: int | None = None,
                     power_db: Sequence[float] | None = None) -> None:
        """Smooth display bins while retaining the raw waterfall history."""
        raw = tuple(max(0.0, min(1.0, float(x))) for x in bins)
        previous_center = self._center_frequency_hz
        previous_rate = self._sample_rate_hz
        geometry_changed = (
            (previous_center is not None and center_frequency_hz != previous_center)
            or (previous_rate is not None and sample_rate_hz != previous_rate)
            or (bool(self._bins) and len(self._bins) != len(raw))
        )
        if geometry_changed:
            # Old rows represent different absolute frequencies; never display
            # them beneath a newly tuned spectrum or reuse their peak hold.
            self._history.clear()
            self._bins = ()
            self._peak_bins = ()
            self._db_floor = None
            self._db_ceiling = None
        if power_db is not None and len(power_db) == len(raw) and raw:
            # Robust percentile-based range, stable across individual spikes.
            ordered = sorted(float(value) for value in power_db)
            noise = ordered[int((len(ordered) - 1) * 0.20)]
            upper = ordered[int((len(ordered) - 1) * 0.98)]
            target_floor = noise - 6.0
            target_ceiling = max(target_floor + 25.0, upper + 6.0)
            if self._db_floor is None or self._db_ceiling is None:
                self._db_floor, self._db_ceiling = target_floor, target_ceiling
            else:
                self._db_floor = 0.9 * self._db_floor + 0.1 * target_floor
                self._db_ceiling = 0.9 * self._db_ceiling + 0.1 * target_ceiling
            span = max(1.0, self._db_ceiling - self._db_floor)
            raw = tuple(max(0.0, min(1.0, (float(value) - self._db_floor) / span))
                        for value in power_db)
        self._center_frequency_hz = center_frequency_hz
        self._sample_rate_hz = sample_rate_hz
        if center_frequency_hz is not None and sample_rate_hz is not None:
            if self._viewport is None:
                self._viewport = SpectrumViewport(
                    float(center_frequency_hz), float(sample_rate_hz), self._recenter_on_tune)
            elif previous_center != center_frequency_hz and self._recenter_on_tune:
                self._viewport = replace(self._viewport, center_hz=float(self._frequency_hz or center_frequency_hz))
            self._constrain_viewport()
        if len(self._bins) == len(raw):
            self._bins = tuple(0.40 * value + 0.60 * old
                               for value, old in zip(raw, self._bins))
            self._peak_bins = (tuple(max(value, peak) for value, peak in zip(self._bins, self._peak_bins))
                               if self._peak_hold_enabled else self._bins)
        else:
            self._bins = raw
            self._peak_bins = raw
        if raw and self._waterfall_enabled:
            self._history.append(raw)
        now = monotonic()
        if now - self._last_spectrum_draw >= 1.0 / self._visualization.max_fps:
            self._last_spectrum_draw = now
            self._schedule_render()

    def set_presets(self, presets: Sequence[tuple[str, int]], on_tune=None) -> None:
        self._presets = tuple(presets)
        self._on_tune = on_tune

    def _schedule_render(self) -> None:
        """Coalesce telemetry and layout updates into one idle-time draw."""
        if not self._draw_pending:
            self._draw_pending = True
            self.after_idle(self._flush_render)

    def _flush_render(self) -> None:
        self._draw_pending = False
        if self.winfo_exists():
            self._render()

    def _render(self) -> None:
        """Render a receiver dashboard, not a bare FFT debug canvas."""
        canvas = self._canvas
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 80 or h < 90:
            return
        ui = self._theme.ui
        compact = h < 260
        header = 54 if compact else 80
        footer = (24 if compact else 32) if (self._mode in ("WFM", "FM") or 76_000_000 <= self._frequency_hz <= 108_000_000) and self._radio_text else 0
        toolbar_height = 34
        scale = 22
        spectrum_top = header + toolbar_height + scale
        self._toolbar_toggle.configure(
            text="HIDE ◀" if self._spectrum_toolbar_visible else "SHOW ▶")
        self._toolbar_toggle.place(x=8, y=header + 2, anchor="nw")
        if self._spectrum_toolbar_visible:
            self._spectrum_controls.place(
                x=self._toolbar_toggle.winfo_reqwidth() + 14,
                y=header + 2, anchor="nw")
        else:
            self._spectrum_controls.place_forget()
        self._mode_label.place(x=w - 12, y=header + 7, anchor="ne")
        plot_bottom = h - footer
        spectrum_height = max(20, int((plot_bottom - spectrum_top) * 0.38))
        waterfall_top = spectrum_top + spectrum_height
        waterfall_height = max(1, plot_bottom - waterfall_top)
        display_bins = self._viewport_row(self._bins)
        display_peaks = self._viewport_row(self._peak_bins) if self._peak_hold_enabled else ()
        display_history = (tuple(self._viewport_row(row) for row in list(self._history)[-128:])
                           if self._waterfall_enabled else ())
        if self._gl_surface is not None:
            self._gl_surface.place(x=0, y=spectrum_top, relwidth=1, height=max(1, plot_bottom-spectrum_top))
            self._gl_surface.update_data(display_bins, display_history,
                                         self._visualization.palette, display_peaks,
                                         tuned_position=self._tuned_position())

        canvas.create_rectangle(0, 0, w, header, fill=ui.surface, outline="")
        canvas.create_rectangle(0, 0, 5, header, fill=ui.accent_primary, outline="")
        canvas.create_line(0, header - 1, w, header - 1, fill=ui.accent_primary, width=2)

        frequency = f"{self._frequency_hz / 1e6:.3f}".rstrip("0").rstrip(".") if self._frequency_hz else "--.-"
        canvas.create_text(w / 2, header - 8, anchor="s",
                           text=f"{frequency} MHz", fill=ui.text,
                           font=("Sans", 25 if compact else 35, "bold"))
        station_title = self._station_title()
        # Preset labels like "90.9 MHz" are not station identities.
        tuned_mhz = f"{self._frequency_hz / 1_000_000:g}"
        if station_title.upper().replace("MHZ", "").replace("FM", "").strip() == tuned_mhz:
            station_title = ""
        if station_title:
            canvas.create_text(14, 12, anchor="nw",
                               text=station_title[:28], width=max(80, w // 3),
                               justify="left", fill=ui.text,
                               font=("Sans", 11 if compact else 15, "bold"))
        # Demodulation is determined by the active radio profile, never
        # selected independently in the spectrum UI.
        mode = "WFM" if self._mode in ("FM", "WFM") else self._mode
        self._mode_label.configure(
            text=f"MODE {mode}" if mode else "")
        if mode == "WFM":
            canvas.create_text(w - 14, header - 8, anchor="se",
                               text="● STEREO" if self._stereo else "MONO",
                               fill=ui.accent_success if self._stereo else ui.text_muted,
                               font=("Sans", 9, "bold"))

        canvas.create_rectangle(0, header + toolbar_height, w, spectrum_top,
                                fill=ui.background, outline="")
        for i in range(5):
            x = 10 + (w - 20) * i / 4
            canvas.create_line(x, spectrum_top - 5, x, spectrum_top,
                               fill=ui.border)
            if self._center_frequency_hz and self._sample_rate_hz:
                hz = (self._viewport.frequency_at(i / 4) if self._viewport is not None else self._center_frequency_hz + (i / 4 - 0.5) * self._sample_rate_hz)
                label = f"{hz / 1_000_000:.3f}"
            else:
                label = f"{i * 25}%"
            canvas.create_text(x, header + toolbar_height + 5, anchor="n",
                               text=label, fill=ui.text_muted,
                               font=("Monospace", 8))
        for i in range(1, 4):
            y = spectrum_top + spectrum_height * i / 4
            canvas.create_line(0, y, w, y, fill=ui.border, dash=(2, 6))
            if self._db_floor is not None and self._db_ceiling is not None:
                level = self._db_ceiling - (self._db_ceiling - self._db_floor) * i / 4
                canvas.create_text(7, y - 2, anchor="sw", text=f"{level:.0f} dB",
                                   fill=ui.text_muted, font=("Monospace", 8))
        if display_bins and self._gl_surface is None:
            points = []
            for i, value in enumerate(display_bins):
                x = i * (w - 1) / max(1, len(display_bins) - 1)
                y = spectrum_top + (spectrum_height - 2) * (1.0 - value)
                points.extend((x, y))
            if len(points) >= 4:
                canvas.create_line(*points, fill=ui.surface_alt, width=5)
                canvas.create_line(*points, fill=ui.accent_primary, width=2)
                peaks = []
                for i, value in enumerate(display_peaks):
                    peaks.extend((i * (w - 1) / max(1, len(display_peaks) - 1),
                                  spectrum_top + (spectrum_height - 2) * (1.0 - value)))
                if len(peaks) >= 4:
                    canvas.create_line(*peaks, fill=ui.accent_success, width=1)

            history = list(display_history)
            # Bound Tk canvas primitives on the 1280x720 touch display. A
            # 64x36 waterfall uses at most 2304 rectangles per refresh.
            x_step = max(4, (w + 63) // 64)
            y_step = max(3, (waterfall_height + 35) // 36)
            if self._waterfall_enabled and history:
                for offset in range(0, waterfall_height, y_step):
                    idx = min(len(history) - 1,
                              offset * len(history) // waterfall_height)
                    values = history[-1 - idx]
                    if not values:
                        continue
                    y = waterfall_top + offset
                    for x in range(0, w, x_step):
                        value = values[min(len(values) - 1, x * len(values) // w)]
                        canvas.create_rectangle(
                            x, y, min(w, x + x_step),
                            min(plot_bottom, y + y_step),
                            fill=self._waterfall_color(value) if self._visualization.palette == "classic"
                            else ("#" + f"{int(value * 255):02x}" * 3), outline="")
        elif self._gl_surface is None:
            canvas.create_text(w / 2, spectrum_top + spectrum_height / 2,
                               text="Waiting for spectrum telemetry",
                               fill=ui.text_muted, font=("Sans", 11))
        if self._gl_surface is None:
            position = self._tuned_position()
            if position is not None:
                x = position * (w - 1)
                canvas.create_line(x, spectrum_top, x, plot_bottom,
                                   fill=ui.accent_success, width=2)
        if self._waterfall_enabled:
            canvas.create_line(0, waterfall_top, w, waterfall_top,
                               fill=ui.accent_primary, width=2)
        if footer:
            canvas.create_rectangle(0, plot_bottom, w, h,
                                    fill=ui.surface, outline=ui.border)
            canvas.create_text(12, plot_bottom + footer / 2, anchor="w",
                               text=self._radio_text[:90],
                               fill=ui.text_muted, font=("Sans", 10))

    def _tuned_position(self) -> float | None:
        """Map the actual tuned frequency onto the visible FFT window."""
        viewport = self._viewport
        if viewport is None or not self._frequency_hz or viewport.span_hz <= 0:
            return None
        position = 0.5 + (self._frequency_hz - viewport.center_hz) / viewport.span_hz
        return position if 0.0 <= position <= 1.0 else None

    def _station_title(self) -> str:
        """Only display station metadata, not the preset's frequency or channel."""
        station = self._station.strip()
        if not station or station == "--":
            return ""
        # A preset can be called "88.1 MHz", "88.1 FM", or "FM 88.1".
        # Those are tuning labels, not station names.
        numeric = r"\\d{2,4}(?:\\.\\d{1,6})?"
        if re.fullmatch(rf"(?:FM\\s*)?{numeric}\\s*(?:MHz|kHz|Hz|FM)?", station, re.I):
            return ""
        if re.fullmatch(rf"FM\\s+{numeric}", station, re.I):
            return ""
        # Also reject a label matching the tuned frequency, regardless of units.
        for divisor in (1_000_000, 1_000, 1):
            if re.fullmatch(rf"{self._frequency_hz / divisor:g}\\s*(?:MHz|kHz|Hz|FM)?", station, re.I):
                return ""
        return station

    @staticmethod
    def _waterfall_color(value: float) -> str:
        value = max(0.0, min(1.0, value))
        if value < 0.33:
            return f"#0000{int(48 + 170 * value / 0.33):02x}"
        if value < 0.66:
            t = (value - 0.33) / 0.33
            return f"#{int(30 * t):02x}{int(190 * t):02x}ff"
        t = (value - 0.66) / 0.34
        return f"#ff{int(190 + 65 * t):02x}{int(40 * (1-t)):02x}"
