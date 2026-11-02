# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Compare post-demodulation audio bandwidth using the same IQ recording."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import wave

import numpy as np
from scipy import signal

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator
from development.sdrpp.native_fm_gain_mode_compare import capture
from hardware_io.sdr import IqBlock

RATE = 2_400_000
AUDIO_RATE = 48_000
BLOCK = 262_144
CUTOFFS = (15_000, 12_000, 10_000, 8_000)


def run(iq_path: Path, output_dir: Path, frequency: int) -> dict:
    receiver = WbfmMonoDemodulator()
    # Keep the 15 kHz reference exactly as ORC currently produces it.
    filters = {hz: signal.butter(6, hz, fs=AUDIO_RATE, output="sos")
               for hz in CUTOFFS if hz != 15_000}
    states = {hz: np.zeros((len(sos), 2), dtype=np.float64)
              for hz, sos in filters.items()}
    stats = {hz: {"samples": 0, "sum_sq": 0.0, "peak": 0.0,
                  "near_clip_samples": 0} for hz in CUTOFFS}
    outputs = {}
    try:
        for hz in CUTOFFS:
            handle = wave.open(str(output_dir / f"audio_{hz // 1000}khz.wav"), "wb")
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(AUDIO_RATE)
            outputs[hz] = handle
        with iq_path.open("rb") as stream:
            while raw := stream.read(BLOCK):
                pcm = receiver.process(IqBlock(
                    samples=raw, center_frequency_hz=frequency,
                    sample_rate_hz=RATE, timestamp_ns=0))
                for hz in CUTOFFS:
                    if hz == 15_000:
                        audio = pcm
                    else:
                        audio, states[hz] = signal.sosfilt(
                            filters[hz], pcm, zi=states[hz])
                    audio = np.asarray(audio, dtype=np.float64)
                    info = stats[hz]
                    info["samples"] += len(audio)
                    info["sum_sq"] += float(np.sum(audio ** 2))
                    info["peak"] = max(info["peak"], float(
                        np.max(np.abs(audio))) if len(audio) else 0.0)
                    info["near_clip_samples"] += int(
                        np.count_nonzero(np.abs(audio) >= 0.999))
                    outputs[hz].writeframes(
                        np.rint(np.clip(audio, -1, 1) * 32767)
                        .astype("<i2").tobytes())
    finally:
        for handle in outputs.values():
            handle.close()
    return {
        f"{hz // 1000}khz": {
            "samples": info["samples"],
            "rms": float(np.sqrt(info["sum_sq"] / info["samples"])),
            "peak": info["peak"],
            "near_clip_samples": info["near_clip_samples"],
        }
        for hz, info in stats.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iq-file", type=Path,
                        help="Existing interleaved unsigned 8-bit IQ capture")
    parser.add_argument("--frequency", type=int, default=104_300_000)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {"frequency_hz": args.frequency, "capture": None}
    if args.iq_file is None:
        if args.seconds <= 0:
            parser.error("--seconds must be positive")
        iq_path = args.output_dir / "manual_30.u8"
        print("Capturing manual 30 dB / both AGC disabled...", flush=True)
        report["capture"] = capture(
            iq_path, args.frequency, 30.0, args.seconds, False)
    else:
        iq_path = args.iq_file
    if not iq_path.is_file():
        parser.error(f"IQ capture not found: {iq_path}")
    print(f"Decoding {iq_path} at four audio bandwidths...", flush=True)
    report["audio"] = run(iq_path, args.output_dir, args.frequency)
    (args.output_dir / "audio_bandwidth_comparison.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("15 kHz is the original ORC output; other variants add a 6th-order low-pass.")
    print("Post-demod clipping counts cannot reveal clipping before this stage.")


if __name__ == "__main__":
    main()
