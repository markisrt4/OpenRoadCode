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
    spectrum: tuple[float, ...] = ()


class _AdaptiveNormalizer:
    """Track a band's recent peak so unlike frequency bands scale independently."""

    def __init__(self, decay: float = 0.995, floor: float = 1e-9) -> None:
        self._peak = floor
        self._decay = decay
        self._floor = floor

    def normalize(self, value: float) -> float:
        self._peak = max(value, self._peak * self._decay, self._floor)
        return max(0.0, min(1.0, value / self._peak))


class AudioAnalyzer:
    """Analyze time-domain PCM samples in both time and frequency domains."""

    def __init__(self, spectrum_band_count: int = 24) -> None:
        self._bass_normalizer = _AdaptiveNormalizer()
        self._mid_normalizer = _AdaptiveNormalizer()
        self._treble_normalizer = _AdaptiveNormalizer()
        self._spectrum_normalizers = tuple(
            _AdaptiveNormalizer() for _ in range(spectrum_band_count)
        )
        self._spectrum_band_count = spectrum_band_count

    def analyze(self, frame: AudioFrame) -> AudioAnalysisState:
        samples = np.asarray(frame.samples, dtype=np.float64)
        if samples.size == 0:
            return AudioAnalysisState(0.0, 0.0, 0.0, 0.0, 0.0)

        peak = float(np.max(np.abs(samples)))
        rms = float(np.sqrt(np.mean(samples * samples)))

        windowed = samples * np.hanning(samples.size)
        spectrum = np.abs(np.fft.rfft(windowed))
        frequencies = np.fft.rfftfreq(samples.size, d=1.0 / frame.sample_rate_hz)

        def band_energy(low_hz: float, high_hz: float) -> float:
            mask = (frequencies >= low_hz) & (frequencies < high_hz)
            if not np.any(mask):
                return 0.0
            return float(math.sqrt(np.mean(spectrum[mask] ** 2)))

        bass_raw = band_energy(20.0, 250.0)
        mid_raw = band_energy(250.0, 4000.0)
        treble_raw = band_energy(4000.0, 16000.0)

        # Logarithmic bands better match musical pitch and human hearing than
        # equal-Hz buckets. They also become the useful input for a graphical
        # spectrum visualizer later.
        edges = np.geomspace(31.25, 16000.0, self._spectrum_band_count + 1)
        spectrum_values = tuple(
            normalizer.normalize(band_energy(float(low), float(high)))
            for low, high, normalizer in zip(
                edges[:-1], edges[1:], self._spectrum_normalizers
            )
        )

        return AudioAnalysisState(
            level=max(0.0, min(1.0, rms * 4.0)),
            peak=max(0.0, min(1.0, peak)),
            bass=self._bass_normalizer.normalize(bass_raw),
            mid=self._mid_normalizer.normalize(mid_raw),
            treble=self._treble_normalizer.normalize(treble_raw),
            spectrum=spectrum_values,
        )
