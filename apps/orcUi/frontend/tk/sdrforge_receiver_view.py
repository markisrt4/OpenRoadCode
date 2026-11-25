# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Native SDRForge spectrum, waterfall, and listener-facing station presentation.

This widget owns no SDR hardware. Composition supplies immutable snapshots and
spectrum bins, keeping transport and DSP outside Tk's UI thread.
"""

from __future__ import annotations

import re
import tkinter as tk
from collections import deque
from collections.abc import Sequence
from dataclasses import replace
from time import monotonic

from ui.radio.radio_visualization_config import (
    RadioRenderer,
    RadioVisualizationConfig,
    load_rf_visualization_settings,
    select_renderer,
)
from ui.radio.sdrforge_spectrum_if import SpectrumViewport
from ui.theme import ThemeBundle
from ui.ui_widget import UiWidget

from .opengl_radio_surface import OpenGLRadioSurface
from .opengl_radio_surface import available as opengl_available
from .sdrforge_render_mixin import SdrForgeRenderMixin
from .sdrforge_viewport_mixin import SdrForgeViewportMixin


class SdrForgeReceiverView(tk.Frame, SdrForgeRenderMixin, SdrForgeViewportMixin, UiWidget):
    """Responsive native receiver visualization for the ORC radio panel."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        theme: ThemeBundle,
        visualization: RadioVisualizationConfig | None = None,
    ) -> None:
        super().__init__(parent, bg=theme.ui.background)
        self._theme = theme
        self._visualization = visualization or RadioVisualizationConfig()
        overrides = load_rf_visualization_settings()
        try:
            self._visualization = replace(
                self._visualization,
                renderer=RadioRenderer(
                    str(overrides.get("renderer", self._visualization.renderer.value))
                ),
                max_fps=int(overrides.get("max_fps", self._visualization.max_fps)),
                waterfall_rows=int(
                    overrides.get("waterfall_rows", self._visualization.waterfall_rows)
                ),
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
        self._pending_viewport_center: float | None = None
        self._recenter_on_tune = False
        self._db_floor: float | None = None
        self._db_ceiling: float | None = None
        self._history: deque[tuple[float, ...]] = deque(maxlen=self._visualization.waterfall_rows)
        self._station = "--"
        self._mode = ""
        self._bandwidth_hz = None
        self._observed_mode = None
        self._frequency_hz = 0
        self._radio_text = ""
        self._stereo = False
        self._signal: float | None = None
        self._presets: tuple[tuple[str, int], ...] = ()
        self._on_tune = None
        self._on_spectrum_tune = None
        self._on_tune_step = None
        self._on_recenter = None
        self._tune_touch_y = None
        self._tune_range: tuple[int, int, int] | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._canvas = tk.Canvas(self, bg=theme.ui.background, bd=0, highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._canvas.bind("<Configure>", lambda _event: self._schedule_render())
        self._canvas.bind("<Button-1>", self._handle_spectrum_click)
        self._canvas.bind("<MouseWheel>", self._handle_tune_wheel)
        self._canvas.bind(
            "<Button-4>",
            lambda event: self._tune_by_wheel(1) if event.y < self._heading_height() else None,
        )
        self._canvas.bind(
            "<Button-5>",
            lambda event: self._tune_by_wheel(-1) if event.y < self._heading_height() else None,
        )
        self._canvas.bind("<ButtonPress-1>", self._tune_touch_start, add="+")
        self._canvas.bind("<B1-Motion>", self._tune_touch_move)
        self._canvas.bind("<ButtonRelease-1>", self._tune_touch_end)
        if self._renderer is RadioRenderer.OPENGL:
            self._gl_surface = OpenGLRadioSurface(self, width=320, height=180)
            self._gl_surface.place(x=0, y=80, relwidth=1, height=180)
            self._gl_surface.bind("<Button-1>", self._handle_spectrum_click)
            self._gl_surface.bind(
                "<MouseWheel>",
                lambda event: (
                    self._tune_by_wheel(1 if event.delta > 0 else -1) if event.delta else None
                ),
            )
            self._gl_surface.bind("<Button-4>", lambda _event: self._tune_by_wheel(1))
            self._gl_surface.bind("<Button-5>", lambda _event: self._tune_by_wheel(-1))
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
                self._spectrum_controls,
                text=label,
                command=callback,
                bg=theme.ui.control_background,
                fg=theme.ui.text,
                relief=tk.FLAT,
                bd=0,
                width=3,
                padx=2,
                pady=3,
                font=("Sans", 10, "bold"),
            )
            button.pack(side="left", padx=2)
            self._spectrum_buttons.append(button)
        self._recenter_button = tk.Button(
            self._spectrum_controls,
            command=self._toggle_recenter,
            bg=theme.ui.control_background,
            fg=theme.ui.text,
            relief=tk.FLAT,
            bd=0,
            padx=6,
            pady=3,
            font=("Sans", 9, "bold"),
        )
        self._recenter_button.pack(side="left", padx=(4, 2))
        self._update_recenter_button()
        # Secondary status belongs with the spectrum tools, not the MHz heading.
        self._mode_label = tk.Label(
            self, text="", bg=theme.ui.surface, fg=theme.ui.text_muted, font=("Sans", 9)
        )
        # Place independently so the label aligns with the right edge of the FFT.
        self._toolbar_toggle = tk.Button(
            self,
            text="HIDE ◀",
            command=self._toggle_spectrum_toolbar,
            bg=theme.ui.control_background,
            fg=theme.ui.text,
            relief=tk.FLAT,
            bd=0,
            padx=6,
            pady=3,
            font=("Sans", 9, "bold"),
        )
        # Preset navigation belongs to RadioPanel, not inside the spectrum.

    def _toggle_spectrum_toolbar(self) -> None:
        """Toggle controls without hiding the button that restores them."""
        self._spectrum_toolbar_visible = not self._spectrum_toolbar_visible
        self._schedule_render()

    def set_spectrum_tune_handler(self, handler) -> None:
        """Receive frequency selections without coupling the widget to radio control."""
        self._on_spectrum_tune = handler

    def set_tune_step_handler(self, handler) -> None:
        """Connect wheel and touch channel navigation to the radio controller."""
        self._on_tune_step = handler

    def _tune_by_wheel(self, direction: int) -> None:
        if self._on_tune_step is not None:
            self._on_tune_step(direction)

    def _heading_height(self) -> int:
        return 54 if self._canvas.winfo_height() < 260 else 80

    def _handle_tune_wheel(self, event) -> None:
        if event.delta and event.y < self._heading_height():
            self._tune_by_wheel(1 if event.delta > 0 else -1)

    def _tune_touch_start(self, event) -> None:
        # Only the station heading acts as a swipe-to-tune surface.
        self._tune_touch_y = event.y if event.y < self._heading_height() else None

    def _tune_touch_move(self, event) -> None:
        if self._tune_touch_y is None:
            return
        delta = self._tune_touch_y - event.y
        if abs(delta) >= 32:
            self._tune_by_wheel(1 if delta > 0 else -1)
            self._tune_touch_y = event.y

    def _tune_touch_end(self, _event) -> None:
        self._tune_touch_y = None

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
            footer = (
                (24 if h < 260 else 32)
                if self._radio_text
                and (self._mode in ("WFM", "FM") or 76_000_000 <= self._frequency_hz <= 108_000_000)
                else 0
            )
            if event.y >= h - footer:
                return
        width = max(1, event.widget.winfo_width())
        position = max(0.0, min(1.0, event.x / width))
        hz = (
            self._viewport.frequency_at(position)
            if self._viewport is not None
            else self._center_frequency_hz + (position - 0.5) * self._sample_rate_hz
        )
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

    def set_station(
        self,
        *,
        frequency_hz: int,
        name: str = "",
        radio_text: str = "",
        stereo: bool = False,
        signal: float | None = None,
        mode: str = "",
        bandwidth_hz: int | None = None,
        observed_mode: str | None = None,
    ) -> None:
        presentation = (
            frequency_hz,
            name,
            radio_text,
            stereo,
            signal,
            mode,
            bandwidth_hz,
            observed_mode,
        )
        if getattr(self, "_last_presentation", None) == presentation:
            return
        self._last_presentation = presentation
        self._mode = mode.upper()
        self._bandwidth_hz = bandwidth_hz
        self._observed_mode = observed_mode
        self._frequency_hz = frequency_hz
        self._station = name or "--"
        self._radio_text = (
            radio_text
            if (self._mode in ("WFM", "FM") or 76_000_000 <= frequency_hz <= 108_000_000)
            else ""
        )
        self._stereo = stereo
        self._signal = signal
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
        self._pending_viewport_center = None
        if self._gl_surface is not None:
            self._gl_surface.update_data((), (), self._visualization.palette)
        self._schedule_render()

    def set_spectrum(
        self,
        bins: Sequence[float],
        *,
        center_frequency_hz: int | None = None,
        sample_rate_hz: int | None = None,
        power_db: Sequence[float] | None = None,
    ) -> None:
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
            raw = tuple(
                max(0.0, min(1.0, (float(value) - self._db_floor) / span)) for value in power_db
            )
        self._center_frequency_hz = center_frequency_hz
        self._sample_rate_hz = sample_rate_hz
        if center_frequency_hz is not None and sample_rate_hz is not None:
            if self._viewport is None:
                self._viewport = SpectrumViewport(
                    float(center_frequency_hz), float(sample_rate_hz), self._recenter_on_tune
                )
            elif previous_center != center_frequency_hz:
                target = getattr(self, "_pending_viewport_center", None)
                self._pending_viewport_center = None
                self._viewport = replace(
                    self._viewport,
                    center_hz=float(center_frequency_hz if target is None else target),
                )
            self._constrain_viewport()
        if len(self._bins) == len(raw):
            self._bins = tuple(
                0.40 * value + 0.60 * old for value, old in zip(raw, self._bins, strict=True)
            )
            self._peak_bins = (
                tuple(
                    max(value, peak)
                    for value, peak in zip(self._bins, self._peak_bins, strict=False)
                )
                if self._peak_hold_enabled
                else self._bins
            )
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
            if re.fullmatch(
                rf"{self._frequency_hz / divisor:g}\\s*(?:MHz|kHz|Hz|FM)?", station, re.I
            ):
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
        return f"#ff{int(190 + 65 * t):02x}{int(40 * (1 - t)):02x}"
