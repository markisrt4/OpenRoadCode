#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Small deterministic smoke test for the shared music analyzer."""
from __future__ import annotations

import argparse
import math

import numpy as np

from controllers.audio.music_analysis import MusicAnalyzer


def tone(
    frequency_hz: float,
    sample_rate_hz: int,
    count: int,
    amplitude: float,
) -> np.ndarray:
    """Create a normalized mono sine-wave test block."""
    t = np.arange(count, dtype=np.float32) / sample_rate_hz
    return (amplitude * np.sin(2.0 * math.pi * frequency_hz * t)).astype(np.float32)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--frequency",
        type=float,
        default=60.0,
        help="test tone frequency in Hz",
    )
    parser.add_argument("--amplitude", type=float, default=0.25)
    parser.add_argument("--sample-rate", type=int, default=48000)
    parser.add_argument("--fft-size", type=int, default=2048)
    args = parser.parse_args()

    analyzer = MusicAnalyzer(fft_size=args.fft_size)
    samples = tone(args.frequency, args.sample_rate, args.fft_size, args.amplitude)
    state = analyzer.analyze(samples, args.sample_rate)

    print(f"input: {args.frequency:.1f} Hz @ amplitude {args.amplitude:.3f}")
    print(f"level:   {state.level:.3f}")
    print(f"bass:    {state.bass:.3f}")
    print(f"mid:     {state.mid:.3f}")
    print(f"treble:  {state.treble:.3f}")
    print("spectrum:")
    for index, value in enumerate(state.spectrum):
        print(f"  {index:02d}: {value:.3f}")
    print("percussion:", state.percussion)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
