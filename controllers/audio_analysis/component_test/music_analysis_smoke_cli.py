# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Deterministic smoke test for the shared music-analysis pipeline.

Run with:
    python -m controllers.audio_analysis.component_test.music_analysis_smoke_cli

This deliberately uses generated PCM instead of a microphone so regressions in
zeroize and spectrum scaling can be separated from browser/PipeWire problems.
"""
from __future__ import annotations

import math
import time

from controllers.audio_analysis.audio_analysis import SpectrumAnalysisMode
from controllers.audio_analysis.music_analysis import MusicAnalyzer
from hardware_io.audio.audio_capture_if import AudioFrame

SAMPLE_RATE = 48_000
FRAME_SAMPLES = 2_400  # 50 ms; enough frames to complete the real zeroize timer quickly.


def tone(frequency_hz: float, amplitude: float, phase: float = 0.0) -> AudioFrame:
    samples = tuple(
        amplitude * math.sin(2.0 * math.pi * frequency_hz * i / SAMPLE_RATE + phase)
        for i in range(FRAME_SAMPLES)
    )
    return AudioFrame(samples=samples, sample_rate_hz=SAMPLE_RATE)


def mixed_frame(*components: tuple[float, float]) -> AudioFrame:
    samples = tuple(
        sum(amplitude * math.sin(2.0 * math.pi * frequency * i / SAMPLE_RATE)
            for frequency, amplitude in components)
        for i in range(FRAME_SAMPLES)
    )
    return AudioFrame(samples=samples, sample_rate_hz=SAMPLE_RATE)


def main() -> int:
    analyzer = MusicAnalyzer(spectrum_band_count=24)
    ambient = mixed_frame((90.0, 0.012), (900.0, 0.008), (7000.0, 0.004))

    analyzer.begin_zeroize(0.5)
    while not analyzer.calibrated:
        state = analyzer.analyze(ambient)
        assert max(state.audio.spectrum, default=0.0) == 0.0, "spectrum must be muted during zeroize"
        assert state.percussion.kick == 0.0, "percussion must be muted during zeroize"
        time.sleep(0.025)

    quiet = analyzer.analyze(ambient)
    assert max(quiet.audio.spectrum, default=0.0) < 0.05, "ambient spectrum was not suppressed"

    music = mixed_frame((70.0, 0.30), (440.0, 0.18), (5000.0, 0.10))
    spectra: dict[SpectrumAnalysisMode, tuple[float, ...]] = {}
    for mode in SpectrumAnalysisMode:
        analyzer.set_spectrum_mode(mode)
        spectra[mode] = analyzer.analyze(music).audio.spectrum
        assert max(spectra[mode], default=0.0) > 0.10, f"{mode.value} spectrum did not react"

    assert spectra[SpectrumAnalysisMode.NATIVE] != spectra[SpectrumAnalysisMode.NORMALIZED], "native and normalized modes collapsed to the same output"
    assert spectra[SpectrumAnalysisMode.HYBRID] != spectra[SpectrumAnalysisMode.NATIVE], "hybrid and native modes collapsed to the same output"
    assert spectra[SpectrumAnalysisMode.HYBRID] != spectra[SpectrumAnalysisMode.NORMALIZED], "hybrid and normalized modes collapsed to the same output"

    print("PASS: zeroize suppresses ambient PCM")
    print("PASS: percussion is muted during zeroize")
    print("PASS: native / normalized / hybrid all react and remain distinct")
    print("PASS: shared MusicAnalyzer smoke test complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
