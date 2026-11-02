# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Capture RTL-SDR asynchronous IQ and report queue integrity."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from hardware_io.sdr.rtl_sdr_source import RtlSdrSource
from development.sdrpp.native_fm_gain_mode_compare import demodulate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", type=int, default=104_300_000)
    parser.add_argument("--sample-rate", type=int, default=2_400_000)
    parser.add_argument("--gain", type=float, default=30.0)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--warmup-seconds", type=float, default=0.0,
                        help="Discard this much initial RF before recording")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    if args.warmup_seconds < 0:
        parser.error("--warmup-seconds must be non-negative")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    iq = args.output_dir / "native_async.u8"
    wav = args.output_dir / "native_async.wav"
    source = RtlSdrSource(acquisition_mode="async", queue_blocks=64)
    target_samples = round(args.seconds * args.sample_rate)
    captured_samples = 0
    discarded_samples = 0
    warmup_target = round(args.warmup_seconds * args.sample_rate)
    started = time.monotonic()
    try:
        source.open()
        source.set_sample_rate(args.sample_rate)
        source.set_center_frequency(args.frequency)
        source.set_gain(args.gain)
        source.set_rtl_agc(False)
        source.start()
        while discarded_samples < warmup_target:
            block = source.read_iq()
            discarded_samples += len(block.samples) // 2
        with iq.open("wb") as stream:
            while captured_samples < target_samples:
                block = source.read_iq()
                remaining_bytes = (target_samples - captured_samples) * 2
                payload = block.samples[:remaining_bytes]
                stream.write(payload)
                captured_samples += len(payload) // 2
        stats = source.get_acquisition_stats()
    finally:
        source.stop()
        source.close()

    print(json.dumps({
        "iq_path": str(iq),
        "rf_seconds": captured_samples / args.sample_rate,
        "warmup_seconds_requested": args.warmup_seconds,
        "warmup_seconds_discarded": discarded_samples / args.sample_rate,
        "wall_seconds": round(time.monotonic() - started, 3),
        "acquisition": stats,
    }, indent=2), flush=True)
    print("Decoding WAV...", flush=True)
    print(json.dumps(demodulate(iq, wav), indent=2), flush=True)
    print(f"WAV: {wav}", flush=True)


if __name__ == "__main__":
    main()
