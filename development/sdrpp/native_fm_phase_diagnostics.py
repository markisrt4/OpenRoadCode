# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Inspect low-amplitude phase jumps in recorded WBFM IQ without modifying DSP."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from scipy import signal

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator
from hardware_io.sdr import IqBlock


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iq-file", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("wbfm-phase-report"))
    parser.add_argument("--block-bytes", type=int, default=262_144)
    args = parser.parse_args()
    if args.block_bytes <= 0 or args.block_bytes % 2:
        parser.error("--block-bytes must be positive and even")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    receiver = WbfmMonoDemodulator()
    magnitudes = []
    phases = []
    audio = []
    # Match the production receiver's filtering, DC subtraction, and phase state.
    with args.iq_file.open("rb") as stream:
        while raw_bytes := stream.read(args.block_bytes):
            if len(raw_bytes) % 2:
                parser.error("IQ file ends with incomplete I/Q pair")
            raw = np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32)
            iq = ((raw[::2] - 127.5) + 1j * (raw[1::2] - 127.5)) / 127.5
            samples = iq.astype(np.complex64)
            for stage, (factor, sos) in enumerate(receiver._rf_stages):
                samples, receiver._rf_states[stage] = signal.sosfilt(
                    sos, samples, zi=receiver._rf_states[stage]
                )
                length = len(samples)
                samples = samples[receiver._rf_phases[stage]::factor]
                receiver._rf_phases[stage] = (
                    receiver._rf_phases[stage] - length
                ) % factor
            if not len(samples):
                continue
            dc, _ = signal.lfilter(
                [receiver._dc_alpha], [1, -(1 - receiver._dc_alpha)],
                samples, zi=[receiver._dc_state * (1 - receiver._dc_alpha)]
            )
            receiver._dc_state = complex(dc[-1])
            samples = samples - dc
            if receiver._previous_iq is None:
                previous = np.concatenate((samples[:1], samples[:-1]))
            else:
                previous = np.concatenate(([receiver._previous_iq], samples[:-1]))
            receiver._previous_iq = complex(samples[-1])
            discriminator = np.angle(samples * np.conj(previous))
            magnitudes.append(np.abs(samples).astype(np.float32))
            phases.append(discriminator.astype(np.float32))

            filtered, receiver._audio_state = signal.sosfilt(
                receiver._audio_sos, discriminator, zi=receiver._audio_state
            )
            length = len(filtered)
            decimated = filtered[receiver._audio_phase::5]
            receiver._audio_phase = (receiver._audio_phase - length) % 5
            decimated = decimated * (240_000 / (2 * np.pi * 75_000))
            pcm, receiver._deemphasis_state = signal.lfilter(
                receiver._deemphasis_b, receiver._deemphasis_a, decimated,
                zi=receiver._deemphasis_state
            )
            audio.append(np.clip(pcm, -1, 1).astype(np.float32))

    if not magnitudes:
        parser.error("No IQ samples processed")
    mag = np.concatenate(magnitudes)
    phase = np.concatenate(phases)
    pcm = np.concatenate(audio)
    p01, p1, p5, p50 = np.percentile(mag, [0.1, 1, 5, 50])
    low = mag <= p1
    large = np.abs(phase) >= 1.0
    both = low & large
    print(f"RF samples (240 kHz): {len(mag):,}; PCM samples: {len(pcm):,}")
    print(f"RF magnitude percentiles: p0.1={p01:.6g} p1={p1:.6g} "
          f"p5={p5:.6g} median={p50:.6g}")
    print(f"Phase abs percentiles (radians): "
          f"p95={np.percentile(np.abs(phase),95):.5f} "
          f"p99={np.percentile(np.abs(phase),99):.5f} "
          f"p99.9={np.percentile(np.abs(phase),99.9):.5f}")
    print(f"Phase >= 1 rad: {np.count_nonzero(large):,} "
          f"({np.mean(large):.3%})")
    print(f"Low magnitude (bottom 1%) AND phase >= 1 rad: "
          f"{np.count_nonzero(both):,} "
          f"({np.mean(large[low]):.3%} of low-magnitude samples)")
    print(f"Phase >= 1 rad outside bottom 1%: "
          f"{np.mean(large[~low]):.3%}")
    print("Note: 1 rad is a diagnostic threshold, not proof of corruption.")

    # Per-10ms windows provide a compact timeline for listening correlation.
    window = 2_400
    report = args.output_dir / "phase_windows.csv"
    with report.open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(("start_seconds", "low_magnitude_pct", "large_phase_pct",
                         "coincident_count", "phase_rms", "pcm_rms"))
        for start in range(0, len(mag), window):
            stop = min(start + window, len(mag))
            a, b = start // 5, (stop + 4) // 5
            writer.writerow((
                f"{start / 240_000:.3f}",
                f"{100 * np.mean(low[start:stop]):.3f}",
                f"{100 * np.mean(large[start:stop]):.3f}",
                int(np.count_nonzero(both[start:stop])),
                f"{np.sqrt(np.mean(phase[start:stop].astype(np.float64) ** 2)):.6f}",
                f"{np.sqrt(np.mean(pcm[a:b].astype(np.float64) ** 2)):.6f}",
            ))
    print(f"10ms timeline: {report}")


if __name__ == "__main__":
    main()
