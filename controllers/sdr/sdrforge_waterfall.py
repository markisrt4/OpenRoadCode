# SPDX-License-Identifier: MIT
"""Bounded, display-independent waterfall history for SDRForge IQ spectra."""

from __future__ import annotations

from collections import deque

from .sdrforge_spectrum import SdrForgeSpectrumFrame


class SdrForgeWaterfall:
    """Retain newest FFT rows without holding unbounded telemetry history."""

    def __init__(self, max_rows: int = 180) -> None:
        if max_rows < 1:
            raise ValueError("max_rows must be positive")
        self._rows: deque[SdrForgeSpectrumFrame] = deque(maxlen=max_rows)

    @property
    def rows(self) -> tuple[SdrForgeSpectrumFrame, ...]:
        """Return oldest-to-newest rows for rendering on the UI thread."""
        return tuple(self._rows)

    @property
    def latest(self) -> SdrForgeSpectrumFrame | None:
        return self._rows[-1] if self._rows else None

    def append(self, frame: SdrForgeSpectrumFrame) -> None:
        """Reset history when the receiver retunes or changes FFT geometry."""
        previous = self.latest
        if previous is not None and (
            frame.center_frequency_hz != previous.center_frequency_hz
            or frame.sample_rate_hz != previous.sample_rate_hz
            or len(frame.power_db) != len(previous.power_db)
            or frame.timestamp_ns < previous.timestamp_ns
        ):
            self._rows.clear()
        self._rows.append(frame)

    def clear(self) -> None:
        self._rows.clear()
