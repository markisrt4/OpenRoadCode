# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Capture-only RTL-SDR IQ experiment with USB read timing and boundary metrics.

No demodulation or playback runs during capture. Read timing is a host-side
indicator, NOT proof of dropped hardware samples. Captures can be decoded
with native_fm_rf_filter_compare or native_fm_phase_protection_compare.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import time

import numpy as np

from hardware_io.sdr import RtlSdrSource


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", type=int, default=104_300_000)
    parser.add_argument("--gain", type=float, default=40.0)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--block-bytes", type=int, default=262_144)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    if args.block_bytes <= 0 or args.block_bytes % 512:
        parser.error("--block-bytes must be a positive multiple of 512")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source = RtlSdrSource(block_bytes=args.block_bytes)
    expected_bytes = int(args.seconds * 2_400_000 * 2)
    rows = []
    total = 0
    prev_end = None
    started = time.perf_counter()
    try:
        source.open()
        source.set_sample_rate(2_400_000)
        source.set_center_frequency(args.frequency)
        source.set_gain(args.gain)
        source.set_rtl_agc(False)
        source.start()
        with (args.output_dir / "capture.u8").open("wb", buffering=1024 * 1024) as output:
            while total < expected_bytes:
                before = time.perf_counter()
                block = source.read_iq()
                after = time.perf_counter()
                raw = block.samples
                output.write(raw)
                iq = np.frombuffer(raw, dtype=np.uint8)
                first = (complex(float(iq[0])-127.5, float(iq[1])-127.5)
                         if len(iq) >= 2 else 0j)
                last = (complex(float(iq[-2])-127.5, float(iq[-1])-127.5)
                        if len(iq) >= 2 else 0j)
                phase_jump = (float(np.angle(first * np.conj(prev_end)))
                              if prev_end is not None else 0.0)
                prev_end = last
                duration = len(raw) / 4_800_000
                rows.append({
                    "block": len(rows),
                    "bytes": len(raw),
                    "read_ms": round((after-before)*1000, 3),
                    "read_start_gap_ms": round((before-started)*1000, 3)
                        if not rows else round((before-previous_after)*1000, 3),
                    "expected_rf_ms": round(duration*1000, 3),
                    "boundary_phase_rad": round(phase_jump, 6),
                })
                previous_after = after
                total += len(raw)
                if len(rows) % 25 == 0:
                    print(f"Captured {total / 4_800_000:.2f}s RF in "
                          f"{after-started:.2f}s wall time", flush=True)
    finally:
        source.stop()
        source.close()
    elapsed = time.perf_counter()-started
    with (args.output_dir / "read_timing.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    reads = np.array([r["read_ms"] for r in rows])
    expected_ms = args.block_bytes / 4_800_000 * 1000
    result = {
        "frequency_hz": args.frequency,
        "sample_rate_hz": 2_400_000,
        "gain_db": args.gain,
        "rtl_agc": False,
        "blocks": len(rows),
        "bytes": total,
        "rf_seconds": total / 4_800_000,
        "wall_seconds": elapsed,
        "throughput_MB_s": total / elapsed / 1e6,
        "expected_block_ms": expected_ms,
        "read_ms_p50": float(np.percentile(reads, 50)),
        "read_ms_p95": float(np.percentile(reads, 95)),
        "read_ms_max": float(np.max(reads)),
        "read_over_1_5x_expected": int(np.sum(reads > 1.5 * expected_ms)),
    }
    (args.output_dir / "capture_metrics.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    print(f"Files: {args.output_dir.resolve()}")
    print("Timing and boundary phase cannot independently prove USB sample loss.")


if __name__ == "__main__":
    main()
