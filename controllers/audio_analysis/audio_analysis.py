# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from hardware_io.audio.audio_capture_if import AudioFrame


@dataclass(frozen=True)
class AudioAnalysisState:
    """Normalized measurements derived from one PCM audio frame."""

    level: float
    peak: float
    bass: float
    mid: float
    treble: float


class AudioAnalyzer:
    """Analyze time-domain PCM samples in both time and frequency domains."""

    def analyze(self, frame: AudioFrame) -> AudioAnalysisState:
        samples = np.asarray(frame.samples, dtype=np.float64)
        if samples.size == 0:
            return AudioAnalysisState(0.0, 0.0, 0.0, 0.0, 0.0)

        # Time-domain measurements.
        peak = float(np.max(np.abs(samples)))
        rms = float(np.sqrt(np.mean(samples * samples)))

        # A Hann window reduces spectral leakage at the edges of each frame.
        windowed = samples * np.hanning(samples.size)
        spectrum = np.abs(np.fft.rfft(windowed))
        frequencies = np.fft.rfftfreq(samples.size, d=1.0 / frame.sample_rate_hz)

        def band_energy(low_hz: float, high_hz: float) -> float:
            mask = (frequencies >= low_hz) & (frequencies < high_hz)
            if not np.any(mask):
                return 0.0
            # RMS magnitude keeps large bins meaningful without simply summing
            # more energy because one band happens to contain more FFT bins.
            return float(math.sqrt(np.mean(spectrum[mask] ** 2)))

        bass_raw = band_energy(20.0, 250.0)
        mid_raw = band_energy(250.0, 4000.0)
        treble_raw = band_energy(4000.0, 16000.0)

        # Initial visualization-friendly normalization. These values are not
        # intended as calibrated acoustic measurements; later we can replace
        # them with adaptive gain/AGC once real music capture is characterized.
        def normalize(value: float, gain: float) -> float:
            return max(0.0, min(1.0, value * gain))

        return AudioAnalysisState(
            level=normalize(rms, 4.0),
            peak=normalize(peak, 1.0),
            bass=normalize(bass_raw, 0.02),
            mid=normalize(mid_raw, 0.02),
            treble=normalize(treble_raw, 0.02),
        )
