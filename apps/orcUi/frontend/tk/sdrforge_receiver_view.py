# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Native SDRForge spectrum, waterfall, and listener-facing station presentation.

This widget owns no SDR hardware. Composition supplies immutable snapshots and
spectrum bins, keeping transport and DSP outside Tk's UI thread.
"""
from __future__ import annotations

import tkinter as tk
from collections import deque
from collections.abc import Sequence

from ui.theme import ThemeBundle


class SdrForgeReceiverView(tk.Frame):
    """Responsive native receiver visualization for the ORC radio panel."""

    def __init__(self, parent: tk.Misc, *, theme: ThemeBundle) -> None:
        super().__init__(parent, bg=theme.ui.background)
        self._theme = theme
        self._bins: tuple[float, ...] = ()
        self._history: deque[tuple[float, ...]] = deque(maxlen=180)
        self._station = "--"
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
        self._canvas.bind("<Configure>", lambda _event: self._render())
        self._preset_frame = tk.Frame(self, bg=theme.ui.surface)
        self._preset_frame.grid(row=1, column=0, sticky="ew")
        self._render_presets()

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        self._theme = theme
        self.configure(bg=theme.ui.background)
        self._canvas.configure(bg=theme.ui.background)
        self._preset_frame.configure(bg=theme.ui.surface)
        self._render_presets()
        self._render()

    def set_station(self, *, frequency_hz: int, name: str = "",
                    radio_text: str = "", stereo: bool = False,
                    signal: float | None = None) -> None:
        self._frequency_hz = frequency_hz
        self._station = name or "--"
        self._radio_text = radio_text
        self._stereo = stereo
        self._signal = signal
        self._render_presets()
        self._render()

    def set_spectrum(self, bins: Sequence[float]) -> None:
        """Accept normalized display magnitudes from 0.0 to 1.0."""
        self._bins = tuple(max(0.0, min(1.0, float(x))) for x in bins)
        if self._bins:
            self._history.append(self._bins)
        self._render()

    def set_presets(self, presets: Sequence[tuple[str, int]], on_tune=None) -> None:
        self._presets = tuple(presets)
        self._on_tune = on_tune
        self._render_presets()

    def _render_presets(self) -> None:
        for child in self._preset_frame.winfo_children():
            child.destroy()
        ui = self._theme.ui
        for name, hz in self._presets[:6]:
            selected = hz == self._frequency_hz
            tk.Button(
                self._preset_frame, text=f"{hz / 1e6:.1f}  {name}",
                command=lambda frequency=hz: self._on_tune(frequency) if self._on_tune else None,
                state=tk.NORMAL if self._on_tune else tk.DISABLED,
                bg=ui.accent_primary if selected else ui.control_background,
                fg=ui.text, activebackground=ui.accent_primary,
                relief=tk.FLAT, padx=5, pady=4,
            ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=3)

    def _render(self) -> None:
        canvas = self._canvas
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 30 or h < 30:
            return
        ui = self._theme.ui
        compact = h < 230
        info_height = 38 if compact else 60
        plot_height = max(12, h - info_height)
        spectrum_height = max(8, int(plot_height * 0.38))
        canvas.create_line(0, spectrum_height, w, spectrum_height,
                           fill=ui.border, width=1)
        if self._bins:
            n = len(self._bins)
            points = []
            for i, value in enumerate(self._bins):
                x = i * (w - 1) / max(1, n - 1)
                y = spectrum_height * (1.0 - value)
                points.extend((x, y))
            if len(points) >= 4:
                canvas.create_line(*points, fill=ui.accent_primary, width=2, smooth=False)
            history = list(self._history)
            available = max(1, plot_height - spectrum_height)
            # Fill the waterfall area by scaling the available history to its
            # height. Use coarse tiles to bound Tk canvas object count.
            x_step = max(3, (w + 199) // 200)
            y_step = max(2, (available + 89) // 90)
            for y_offset in range(0, available, y_step):
                history_index = min(len(history) - 1,
                                    y_offset * len(history) // available)
                values = history[-1 - history_index]
                y = spectrum_height + y_offset
                for x in range(0, w, x_step):
                    value = values[min(len(values) - 1, x * len(values) // w)]
                    canvas.create_rectangle(
                        x, y, min(w, x + x_step), min(plot_height, y + y_step),
                        fill=self._waterfall_color(value), outline="",
                    )
        else:
            canvas.create_text(w / 2, plot_height / 2, text="Waiting for spectrum…",
                               fill=ui.text_muted, font=("Sans", 10))
        canvas.create_rectangle(0, plot_height, w, h, fill=ui.surface, outline=ui.border)
        canvas.create_text(10, plot_height + (12 if compact else 18), anchor="w",
                           text=self._station,
                           fill=ui.text, font=("Sans", 11 if compact else 14, "bold"))
        if self._stereo:
            canvas.create_text(w - 10, plot_height + (12 if compact else 18), anchor="e",
                               text="STEREO", fill=ui.accent_success,
                               font=("Sans", 9, "bold"))
        detail = self._radio_text
        if detail:
            canvas.create_text(10, h - 7, anchor="sw", text=detail[:90],
                               fill=ui.text_muted, font=("Sans", 9))

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
