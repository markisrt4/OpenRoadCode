# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Acquisition viewport controls for the native SDRForge presentation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from ui.radio.radio_visualization_config import (
    load_rf_visualization_settings,
    save_rf_visualization_settings,
)


class SdrForgeViewportMixin:
    """Manage the visible RF window independently of listening frequency."""

    def _update_recenter_button(self) -> None:
        self._recenter_button.configure(text="CENTER", fg=self._theme.ui.text)

    def set_recenter_handler(self, handler) -> None:
        self._on_recenter = handler

    def _toggle_recenter(self) -> None:
        if self._on_recenter is not None:
            self._on_recenter()
        if self._viewport is not None and self._frequency_hz:
            self._viewport = replace(
                self._viewport, center_hz=float(self._frequency_hz), recenter_on_tune=False
            )
            self._constrain_viewport()
            self._schedule_render()

    def set_recenter_on_tune(self, enabled: bool) -> None:
        self._recenter_on_tune = False
        if self._viewport is not None:
            self._viewport = replace(self._viewport, recenter_on_tune=False)
            self._constrain_viewport()
        settings = load_rf_visualization_settings()
        settings["recenter_on_tune"] = False
        save_rf_visualization_settings(settings)
        self._update_recenter_button()
        self._schedule_render()

    def _constrain_viewport(self) -> None:
        """Keep the visible window entirely inside acquired RF bandwidth."""
        viewport = self._viewport
        if viewport is None or self._center_frequency_hz is None or not self._sample_rate_hz:
            return
        rate = float(self._sample_rate_hz)
        span = min(viewport.span_hz, rate)
        margin = (rate - span) / 2
        center = max(
            self._center_frequency_hz - margin,
            min(viewport.center_hz, self._center_frequency_hz + margin),
        )
        self._viewport = replace(viewport, center_hz=center, span_hz=span)

    def set_acquisition_pan_handler(self, handler) -> None:
        self._on_acquisition_pan = handler

    def pan_spectrum(self, fraction: float) -> None:
        if self._viewport is not None:
            self._recenter_on_tune = False
            self._update_recenter_button()
            if self._sample_rate_hz and self._viewport.span_hz >= self._sample_rate_hz:
                self._viewport = self._viewport.zoom(0.7)
            target = self._viewport.pan(fraction)
            self._viewport = replace(target, recenter_on_tune=False)
            self._constrain_viewport()
            if target.center_hz != self._viewport.center_hz:
                handler = getattr(self, "_on_acquisition_pan", None)
                if handler is not None:
                    handler(round(target.center_hz))
            self._schedule_render()

    def zoom_spectrum(self, factor: float) -> None:
        if self._viewport is not None:
            self._viewport = self._viewport.zoom(
                factor, max_span_hz=float(self._sample_rate_hz or self._viewport.span_hz)
            )
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
                min(
                    len(row) - 1,
                    max(
                        0,
                        int((viewport.frequency_at(i / max(1, length - 1)) - source_start) * scale),
                    ),
                )
                for i in range(length)
            )
        )
