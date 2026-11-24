# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Native SDRForge spectrum, waterfall, and listener-facing station presentation.

This widget owns no SDR hardware. Composition supplies immutable snapshots and
spectrum bins, keeping transport and DSP outside Tk's UI thread.
"""

from __future__ import annotations

import tkinter as tk
from ui.ui_widget import UiWidget
from dataclasses import replace
import re
from time import monotonic

from ui.radio.radio_visualization_config import (
    RadioRenderer,
    RadioVisualizationConfig,
    select_renderer,
    load_rf_visualization_settings,
    save_rf_visualization_settings,
)
from collections import deque
from collections.abc import Sequence

from ui.radio.sdrforge_spectrum_if import SpectrumViewport
from ui.theme import ThemeBundle
from .opengl_radio_surface import OpenGLRadioSurface, available as opengl_available


class SdrForgeRenderMixin:
    """Draw spectrum and waterfall from cached presentation data."""

    def _passband(self) -> tuple[float, float] | None:
        viewport = self._viewport
        if viewport is None or not self._frequency_hz or viewport.span_hz <= 0:
            return None
        bandwidth = self._bandwidth_hz or {
            "FM": 200000,
            "WFM": 200000,
            "NFM": 12500,
            "AM": 10000,
        }.get(self._mode, 0)
        if bandwidth <= 0:
            return None
        center = 0.5 + (self._frequency_hz - viewport.center_hz) / viewport.span_hz
        half = bandwidth / (2 * viewport.span_hz)
        if self._mode in ("AM", "NFM"):
            half = max(half, 2.0 / max(1, self._canvas.winfo_width()))
        left, right = max(0.0, center - half), min(1.0, center + half)
        return (left, right) if left < right else None

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
        footer = (
            (24 if compact else 32)
            if (self._mode in ("WFM", "FM") or 76_000_000 <= self._frequency_hz <= 108_000_000)
            and self._radio_text
            else 0
        )
        toolbar_height = 34
        scale = 22
        spectrum_top = header + toolbar_height + scale
        self._toolbar_toggle.configure(
            text="HIDE ◀" if self._spectrum_toolbar_visible else "SHOW ▶"
        )
        self._toolbar_toggle.place(x=8, y=header + 2, anchor="nw")
        if self._spectrum_toolbar_visible:
            self._spectrum_controls.place(
                x=self._toolbar_toggle.winfo_reqwidth() + 14, y=header + 2, anchor="nw"
            )
        else:
            self._spectrum_controls.place_forget()
        self._mode_label.place(x=w - 12, y=header + 7, anchor="ne")
        plot_bottom = h - footer
        spectrum_height = max(20, int((plot_bottom - spectrum_top) * 0.38))
        waterfall_top = spectrum_top + spectrum_height
        waterfall_height = max(1, plot_bottom - waterfall_top)
        display_bins = self._viewport_row(self._bins)
        display_peaks = self._viewport_row(self._peak_bins) if self._peak_hold_enabled else ()
        display_history = (
            tuple(self._viewport_row(row) for row in list(self._history)[-128:])
            if self._waterfall_enabled
            else ()
        )
        if self._gl_surface is not None:
            self._gl_surface.place(
                x=0, y=spectrum_top, relwidth=1, height=max(1, plot_bottom - spectrum_top)
            )
            self._gl_surface.update_data(
                display_bins,
                display_history,
                self._visualization.palette,
                display_peaks,
                tuned_position=self._tuned_position(),
                passband=self._passband(),
            )

        canvas.create_rectangle(0, 0, w, header, fill=ui.surface, outline="")
        canvas.create_rectangle(0, 0, 5, header, fill=ui.accent_primary, outline="")
        canvas.create_line(0, header - 1, w, header - 1, fill=ui.accent_primary, width=2)

        frequency = (
            f"{self._frequency_hz / 1e6:.3f}".rstrip("0").rstrip(".")
            if self._frequency_hz
            else "--.-"
        )
        canvas.create_text(
            w / 2,
            header - 8,
            anchor="s",
            text=f"{frequency} MHz",
            fill=ui.text,
            font=("Sans", 25 if compact else 35, "bold"),
        )
        station_title = self._station_title()
        # Preset labels like "90.9 MHz" are not station identities.
        tuned_mhz = f"{self._frequency_hz / 1_000_000:g}"
        if station_title.upper().replace("MHZ", "").replace("FM", "").strip() == tuned_mhz:
            station_title = ""
        if station_title:
            canvas.create_text(
                14,
                12,
                anchor="nw",
                text=station_title[:28],
                width=max(80, w // 3),
                justify="left",
                fill=ui.text,
                font=("Sans", 11 if compact else 15, "bold"),
            )
        # Demodulation is determined by the active radio profile, never
        # selected independently in the spectrum UI.
        mode = "WFM" if self._mode in ("FM", "WFM") else self._mode
        mismatch = self._observed_mode and self._observed_mode != mode
        self._mode_label.configure(
            text=f"MODE {mode} ≠ {self._observed_mode}"
            if mismatch
            else f"MODE {mode}"
            if mode
            else "",
            fg=ui.accent_danger if mismatch else ui.text_muted,
            bg=ui.surface,
        )
        if mode == "WFM":
            canvas.create_text(
                w - 14,
                header - 8,
                anchor="se",
                text="● STEREO" if self._stereo else "MONO",
                fill=ui.accent_success if self._stereo else ui.text_muted,
                font=("Sans", 9, "bold"),
            )

        canvas.create_rectangle(
            0, header + toolbar_height, w, spectrum_top, fill=ui.background, outline=""
        )
        for i in range(5):
            x = 10 + (w - 20) * i / 4
            canvas.create_line(x, spectrum_top - 5, x, spectrum_top, fill=ui.border)
            if self._center_frequency_hz and self._sample_rate_hz:
                hz = (
                    self._viewport.frequency_at(i / 4)
                    if self._viewport is not None
                    else self._center_frequency_hz + (i / 4 - 0.5) * self._sample_rate_hz
                )
                label = f"{hz / 1_000_000:.3f}"
            else:
                label = f"{i * 25}%"
            canvas.create_text(
                x,
                header + toolbar_height + 5,
                anchor="n",
                text=label,
                fill=ui.text_muted,
                font=("Monospace", 8),
            )
        for i in range(1, 4):
            y = spectrum_top + spectrum_height * i / 4
            canvas.create_line(0, y, w, y, fill=ui.border, dash=(2, 6))
            if self._db_floor is not None and self._db_ceiling is not None:
                level = self._db_ceiling - (self._db_ceiling - self._db_floor) * i / 4
                canvas.create_text(
                    7,
                    y - 2,
                    anchor="sw",
                    text=f"{level:.0f} dB",
                    fill=ui.text_muted,
                    font=("Monospace", 8),
                )
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
                    peaks.extend(
                        (
                            i * (w - 1) / max(1, len(display_peaks) - 1),
                            spectrum_top + (spectrum_height - 2) * (1.0 - value),
                        )
                    )
                if len(peaks) >= 4:
                    canvas.create_line(*peaks, fill=ui.accent_success, width=1)

            history = list(display_history)
            # Bound Tk canvas primitives on the 1280x720 touch display. A
            # 64x36 waterfall uses at most 2304 rectangles per refresh.
            x_step = max(4, (w + 63) // 64)
            y_step = max(3, (waterfall_height + 35) // 36)
            if self._waterfall_enabled and history:
                for offset in range(0, waterfall_height, y_step):
                    idx = min(len(history) - 1, offset * len(history) // waterfall_height)
                    values = history[-1 - idx]
                    if not values:
                        continue
                    y = waterfall_top + offset
                    for x in range(0, w, x_step):
                        value = values[min(len(values) - 1, x * len(values) // w)]
                        canvas.create_rectangle(
                            x,
                            y,
                            min(w, x + x_step),
                            min(plot_bottom, y + y_step),
                            fill=self._waterfall_color(value)
                            if self._visualization.palette == "classic"
                            else ("#" + f"{int(value * 255):02x}" * 3),
                            outline="",
                        )
        elif self._gl_surface is None:
            canvas.create_text(
                w / 2,
                spectrum_top + spectrum_height / 2,
                text="Waiting for spectrum telemetry",
                fill=ui.text_muted,
                font=("Sans", 11),
            )
        if self._gl_surface is None:
            band = self._passband()
            if band is not None:
                canvas.create_rectangle(
                    band[0] * (w - 1),
                    spectrum_top,
                    band[1] * (w - 1),
                    plot_bottom,
                    fill=ui.accent_success,
                    stipple="gray25",
                    outline="",
                )
            position = self._tuned_position()
            if position is not None:
                x = position * (w - 1)
                canvas.create_line(x, spectrum_top, x, plot_bottom, fill=ui.accent_success, width=2)
        if self._waterfall_enabled:
            canvas.create_line(0, waterfall_top, w, waterfall_top, fill=ui.accent_primary, width=2)
        if footer:
            canvas.create_rectangle(0, plot_bottom, w, h, fill=ui.surface, outline=ui.border)
            canvas.create_text(
                12,
                plot_bottom + footer / 2,
                anchor="w",
                text=self._radio_text[:90],
                fill=ui.text_muted,
                font=("Sans", 10),
            )
