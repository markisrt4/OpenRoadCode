# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Bounded waterfall history for native SDR spectrum frames."""

import numpy as np

from controllers.radio.spectrum.spectrum_analyzer import SpectrumFrame


class WaterfallHistory:
    """Store a fixed number of recent power spectra, newest first."""

    def __init__(self, rows: int = 180, min_db: float = -85, max_db: float = -15) -> None:
        if rows <= 0:
            raise ValueError("rows must be positive")
        if not np.isfinite(min_db) or not np.isfinite(max_db) or min_db >= max_db:
            raise ValueError("waterfall dB limits must be finite and increasing")
        self.rows = rows
        self.min_db = min_db
        self.max_db = max_db
        self._history: np.ndarray | None = None
        self._config: tuple[int, int, int] | None = None
        self._write_index = 0
        self._count = 0

    def append(self, frame: SpectrumFrame) -> None:
        """Append a spectrum; reset history when tuning or FFT dimensions change."""
        power = np.asarray(frame.power_db, dtype=np.float32)
        if power.ndim != 1 or power.size == 0 or not np.all(np.isfinite(power)):
            raise ValueError("waterfall requires finite, nonempty spectrum bins")
        config = (frame.center_frequency_hz, frame.sample_rate_hz, len(power))
        if config != self._config:
            self._config = config
            self._history = np.full((self.rows, len(power)), self.min_db, dtype=np.float32)
            self._write_index = 0
            self._count = 0
        assert self._history is not None
        self._history[self._write_index] = power
        self._write_index = (self._write_index + 1) % self.rows
        self._count = min(self._count + 1, self.rows)

    def image(self) -> np.ndarray:
        """Return a normalized intensity image, newest row first (0..1)."""
        if self._history is None:
            return np.zeros((self.rows, 0), dtype=np.float32)
        indices = (self._write_index - 1 - np.arange(self.rows)) % self.rows
        values = self._history[indices]
        return np.clip((values - self.min_db) / (self.max_db - self.min_db), 0, 1)
