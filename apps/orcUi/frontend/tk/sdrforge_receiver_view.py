# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Native SDRForge spectrum, waterfall, and listener-facing station presentation.

This widget owns no SDR hardware. Composition supplies immutable snapshots and
spectrum bins, keeping transport and DSP outside Tk's UI thread.
"""
from __future__ import annotations

import tkinter as tk
import re
from time import monotonic

from ui.radio.radio_visualization_config import RadioRenderer, RadioVisualizationConfig, select_renderer
from collections import deque
from collections.abc import Sequence

from ui.theme import ThemeBundle
from .opengl_radio_surface import OpenGLRadioSurface, available as opengl_available


class SdrForgeReceiverView(tk.Frame):
    """Responsive native receiver visualization for the ORC radio panel."""

    def __init__(self, parent: tk.Misc, *, theme: ThemeBundle,
                 visualization: RadioVisualizationConfig | None = None) -> None:
        super().__init__(parent, bg=theme.ui.background)
        self._theme = theme
        self._visualization = visualization or RadioVisualizationConfig()
        self._renderer = select_renderer(self._visualization, opengl_available=opengl_available())
        self._gl_surface = None
        self._last_spectrum_draw = 0.0
        self._draw_pending = False
        self._bins: tuple[float, ...] = ()
        self._history: deque[tuple[float, ...]] = deque(maxlen=self._visualization.waterfall_rows)
        self._station = "--"
        self._mode = ""
        self._frequency_hz = 0
        self._radio_text = ""
        self._stereo = False
        self._signal: float | None = None
        self._presets: tuple[tuple[str, int], ...] = ()
        self._on_tune = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._canvas = tk.Canvas(self, bg=theme.ui.background, bd=0, highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._canvas.bind("<Configure>", lambda _event: self._schedule_render())
        if self._renderer is RadioRenderer.OPENGL:
            self._gl_surface = OpenGLRadioSurface(self, width=320, height=180)
            self._gl_surface.place(x=0, y=80, relwidth=1, height=180)
        # Preset navigation belongs to RadioPanel, not inside the spectrum.

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        self._theme = theme
        self.configure(bg=theme.ui.background)
        self._canvas.configure(bg=theme.ui.background)
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
        self._radio_text = radio_text if self._mode in ("WFM", "FM") else ""
        self._stereo = stereo
        self._signal = signal
        self._schedule_render()

    def set_spectrum(self, bins: Sequence[float]) -> None:
        """Accept normalized display magnitudes from 0.0 to 1.0."""
        self._bins = tuple(max(0.0, min(1.0, float(x))) for x in bins)
        if self._bins:
            self._history.append(self._bins)
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
        footer = (24 if compact else 32) if self._mode in ("WFM", "FM") and self._radio_text else 0
        scale = 22
        spectrum_top = header + scale
        plot_bottom = h - footer
        spectrum_height = max(20, int((plot_bottom - spectrum_top) * 0.38))
        waterfall_top = spectrum_top + spectrum_height
        waterfall_height = max(1, plot_bottom - waterfall_top)
        if self._gl_surface is not None:
            self._gl_surface.place(x=0, y=spectrum_top, relwidth=1, height=max(1, plot_bottom-spectrum_top))
            self._gl_surface.update_data(self._bins, tuple(self._history), self._visualization.palette)

        canvas.create_rectangle(0, 0, w, header, fill=ui.surface, outline="")
        canvas.create_rectangle(0, 0, 5, header, fill=ui.accent_primary, outline="")
        canvas.create_line(0, header - 1, w, header - 1, fill=ui.accent_primary, width=2)

        frequency = f"{self._frequency_hz / 1e6:.3f}".rstrip("0").rstrip(".") if self._frequency_hz else "--.-"
        canvas.create_text(14, header - 8, anchor="sw",
                           text=f"{frequency} MHz", fill=ui.text,
                           font=("Sans", 25 if compact else 35, "bold"))
        canvas.create_text(w - 14, 12, anchor="ne",
                           text=self._station_title()[:28], width=max(80, w // 2 - 18), justify="right", fill=ui.text,
                           font=("Sans", 11 if compact else 15, "bold"))
        if self._mode in ("WFM", "FM"):
            canvas.create_text(w - 14, header - 8, anchor="se",
                               text="● STEREO" if self._stereo else "MONO",
                               fill=ui.accent_success if self._stereo else ui.text_muted,
                               font=("Sans", 9, "bold"))

        # Scale labels represent relative FFT position until the spectrum
        # contract supplies center frequency and bin spacing.
        canvas.create_rectangle(0, header, w, spectrum_top,
                                fill=ui.background, outline="")
        for i in range(5):
            x = 10 + (w - 20) * i / 4
            canvas.create_line(x, spectrum_top - 5, x, spectrum_top,
                               fill=ui.border)
            canvas.create_text(x, header + 5, anchor="n",
                               text=f"{i * 25}%", fill=ui.text_muted,
                               font=("Monospace", 8))
        for i in range(1, 4):
            y = spectrum_top + spectrum_height * i / 4
            canvas.create_line(0, y, w, y, fill=ui.border, dash=(2, 6))
        if self._bins and self._gl_surface is None:
            points = []
            for i, value in enumerate(self._bins):
                x = i * (w - 1) / max(1, len(self._bins) - 1)
                y = spectrum_top + (spectrum_height - 2) * (1.0 - value)
                points.extend((x, y))
            if len(points) >= 4:
                canvas.create_line(*points, fill=ui.surface_alt, width=5)
                canvas.create_line(*points, fill=ui.accent_primary, width=2)
                canvas.create_line(w / 2, spectrum_top, w / 2, plot_bottom, fill=ui.accent_success, width=1)
            history = list(self._history)
            x_step = max(4, (w + 95) // 96)
            y_step = max(3, (waterfall_height + 47) // 48)
            for offset in range(0, waterfall_height, y_step):
                idx = min(len(history) - 1,
                          offset * len(history) // waterfall_height)
                values = history[-1 - idx]
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
        canvas.create_line(0, waterfall_top, w, waterfall_top,
                           fill=ui.accent_primary, width=2)
        if footer:
            canvas.create_rectangle(0, plot_bottom, w, h,
                                    fill=ui.surface, outline=ui.border)
            canvas.create_text(12, plot_bottom + footer / 2, anchor="w",
                               text=self._radio_text[:90],
                               fill=ui.text_muted, font=("Sans", 10))

    def _station_title(self) -> str:
        """Only show a real station label, never a second frequency."""
        station = self._station.strip()
        if station in ("", "--"):
            return ""
        frequency_only = r"^(?:\\d{2,4}(?:\\.\\d{1,6})?\\s*(?:MHz|kHz|Hz)?|FM\\s+Radio)$"
        if re.fullmatch(frequency_only, station, flags=re.IGNORECASE):
            return ""
        title = re.sub(r"\\b\\d{2,4}\\.\\d{1,6}\\s*(?:MHz|kHz|Hz)?\\b", "", station, flags=re.IGNORECASE).strip(" -/")
        return title

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
