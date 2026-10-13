# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Display-only smoothing and peak hold for native RF spectrum frames."""

from dataclasses import dataclass

import numpy as np

from controllers.radio.spectrum.spectrum_analyzer import SpectrumFrame


@dataclass(frozen=True)
class SpectrumDisplayFrame:
    """Spectrum traces with identical frequency coordinates."""

    smoothed_db: tuple[float, ...]
    peak_db: tuple[float, ...]


class SpectrumDisplayProcessor:
    """Exponential smoothing and persistent per-bin peak hold in dB."""

    def __init__(self, alpha: float = 0.2) -> None:
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self._smoothed: np.ndarray | None = None
        self._peak: np.ndarray | None = None
        self._configuration: tuple[int, int, int] | None = None

    def reset_peaks(self) -> None:
        """Clear peak hold without resetting the current smoothing history."""
        self._peak = None

    def process(self, frame: SpectrumFrame) -> SpectrumDisplayFrame:
        values = np.asarray(frame.power_db, dtype=np.float64)
        if values.ndim != 1 or not values.size or not np.all(np.isfinite(values)):
            raise ValueError("Spectrum power bins must be nonempty and finite")
        configuration = (frame.center_frequency_hz, frame.sample_rate_hz, len(values))
        if configuration != self._configuration:
            self._configuration = configuration
            self._smoothed = None
            self._peak = None

        if self._smoothed is None:
            self._smoothed = values.copy()
        else:
            self._smoothed = self.alpha * values + (1 - self.alpha) * self._smoothed
        if self._peak is None:
            self._peak = self._smoothed.copy()
        else:
            np.maximum(self._peak, self._smoothed, out=self._peak)
        return SpectrumDisplayFrame(
            smoothed_db=tuple(self._smoothed),
            peak_db=tuple(self._peak),
        )
