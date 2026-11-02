# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Compare tuner AGC against fixed tuner gain with RTL digital AGC disabled."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import wave

import numpy as np

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator
from hardware_io.sdr import IqBlock, RtlSdrSource

RATE = 2_400_000
BLOCK = 262_144


def capture(path: Path, frequency: int, gain: float | None,
            seconds: float) -> dict:
    source = RtlSdrSource(block_bytes=BLOCK)
    total = 0
    expected = int(seconds * RATE * 2)
    read_times = []
    levels = []
    start = time.perf_counter()
    try:
        source.open()
        source.set_sample_rate(RATE)
        source.set_center_frequency(frequency)
        source.set_gain(gain)
        source.set_rtl_agc(False)
        source.start()
        with path.open("wb", buffering=1024 * 1024) as output:
            while total < expected:
                before = time.perf_counter()
                block = source.read_iq()
                read_times.append((time.perf_counter() - before) * 1000)
                raw = block.samples
                output.write(raw)
                values = np.frombuffer(raw, dtype=np.uint8)
                levels.append((
                    float(np.mean((values.astype(np.float32)-127.5)**2)),
                    int(np.count_nonzero((values <= 2) | (values >= 253))),
                ))
                total += len(raw)
    finally:
        source.stop()
        source.close()
    return {
        "mode": "tuner_agc" if gain is None else "manual",
        "gain_db_requested": gain,
        "rtl_agc": False,
        "rf_seconds": total / (2 * RATE),
        "wall_seconds": time.perf_counter() - start,
        "iq_rms_normalized": float(np.sqrt(
            sum(power for power, _ in levels) / len(levels)) / 127.5),
        "near_rail_fraction": sum(rail for _, rail in levels) / total,
        "read_ms_p95": float(np.percentile(read_times, 95)),
        "read_ms_max": float(np.max(read_times)),
    }


def demodulate(path: Path, output: Path) -> dict:
    receiver = WbfmMonoDemodulator()
    count = 0
    sum_squares = 0.0
    with path.open("rb") as stream, wave.open(str(output), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48_000)
        while raw := stream.read(BLOCK):
            pcm = receiver.process(IqBlock(
                samples=raw, center_frequency_hz=104_300_000,
                sample_rate_hz=RATE, timestamp_ns=0
            ))
            wav.writeframes(np.rint(np.clip(pcm, -1, 1) * 32767)
                            .astype("<i2").tobytes())
            count += len(pcm)
            sum_squares += float(np.sum(pcm.astype(np.float64)**2))
    return {"pcm_samples": count, "audio_rms": float(np.sqrt(sum_squares/count))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", type=int, default=104_300_000)
    parser.add_argument("--gain", type=float, default=40.0)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {"frequency_hz": args.frequency, "sample_rate_hz": RATE,
              "captures": {}}
    for name, gain in (("tuner_agc", None), ("manual", args.gain)):
        print(f"Capturing {name}...", flush=True)
        iq_path = args.output_dir / f"{name}.u8"
        metrics = capture(iq_path, args.frequency, gain, args.seconds)
        metrics.update(demodulate(iq_path, args.output_dir / f"{name}.wav"))
        report["captures"][name] = metrics
        print(f"{name}: RF RMS={metrics['iq_rms_normalized']:.4f}, "
              f"near rails={metrics['near_rail_fraction']:.4%}, "
              f"audio RMS={metrics['audio_rms']:.4f}", flush=True)
    (args.output_dir / "gain_comparison.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    print("Captures are sequential, so broadcast content can differ.")
    print(f"Files: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
