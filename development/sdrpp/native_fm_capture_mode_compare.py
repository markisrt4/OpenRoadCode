# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Compare ORC synchronous RTL-SDR capture with rtl_sdr CLI capture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np

from development.sdrpp.native_fm_gain_mode_compare import capture, demodulate

RATE = 2_400_000
GAIN = 30.0


def inspect_iq(path: Path) -> dict:
    """Report IQ level, rails, and suspiciously large adjacent sample changes."""
    total = 0
    rails = 0
    sum_sq = 0.0
    large_steps = 0
    previous = None
    started = time.monotonic()
    with path.open("rb") as stream:
        while raw := stream.read(262144 * 4):
            values = np.frombuffer(raw, dtype=np.uint8)
            if len(values) % 2:
                raise ValueError(f"Odd IQ byte count in {path}")
            iq = (values.reshape(-1, 2).astype(np.float32) - 127.5) / 127.5
            total += len(iq)
            rails += int(np.count_nonzero((values <= 2) | (values >= 253)))
            sum_sq += float(np.sum(iq ** 2))
            if total and total % (RATE * 5) < len(iq):
                print(f"  IQ inspected: {total / RATE:.1f}s, elapsed {time.monotonic() - started:.1f}s", flush=True)
            if previous is not None and len(iq):
                first = iq[0]
                if float(np.sum((first - previous) ** 2)) > 1.0:
                    large_steps += 1
            if len(iq) > 1:
                delta = np.diff(iq, axis=0)
                large_steps += int(np.count_nonzero(
                    delta[:, 0] ** 2 + delta[:, 1] ** 2 > 1.0))
            if len(iq):
                previous = iq[-1].copy()
    return {
        "complex_samples": total,
        "rf_seconds": total / RATE,
        "component_rms": float(np.sqrt(sum_sq / (2 * total))) if total else 0.0,
        "near_rail_fraction": rails / (2 * total) if total else 0.0,
        "adjacent_iq_steps_over_1": large_steps,
        "adjacent_iq_step_fraction": large_steps / max(total - 1, 1),
    }


def cli_capture(path: Path, frequency: int, seconds: float) -> dict:
    exe = shutil.which("rtl_sdr")
    if exe is None:
        raise RuntimeError("rtl_sdr not found. Install rtl-sdr CLI utilities.")
    # -n is a count of complex IQ samples, not bytes. Keep it divisible
    # by the ORC capture block size to avoid tail-size comparison effects.
    samples_per_block = 262144 // 2
    samples = int(np.ceil(seconds * RATE / samples_per_block)) * samples_per_block
    command = [exe, "-f", str(frequency), "-s", str(RATE),
               "-g", str(GAIN), "-n", str(samples), str(path)]
    print("CLI capture:", " ".join(command), flush=True)
    print("Waiting for rtl_sdr to finish; timeout is enabled.", flush=True)
    start = time.perf_counter()
    timeout = max(45.0, seconds * 5.0)
    try:
        proc = subprocess.run(command, stdout=subprocess.DEVNULL,
                              stderr=subprocess.PIPE, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        stderr = exc.stderr or b""
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"rtl_sdr timed out after {timeout:.0f}s. "
            f"Captured {path.stat().st_size if path.exists() else 0} bytes. "
            f"stderr tail:\n{stderr[-2000:]}") from exc
    if proc.returncode:
        raise RuntimeError(f"rtl_sdr failed ({proc.returncode}):\n{proc.stderr}")
    expected_bytes = samples * 2
    if path.stat().st_size != expected_bytes:
        raise RuntimeError(f"CLI IQ file size {path.stat().st_size} != {expected_bytes}")
    return {"wall_seconds": time.perf_counter() - start,
            "command": command, "stderr_tail": proc.stderr[-1500:]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", type=int, default=104_300_000)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--skip-cli", action="store_true",
                        help="Inspect/decode ORC sync capture only; skip rtl_sdr")
    parser.add_argument("--reuse-sync", action="store_true",
                        help="Reuse existing orc_sync.u8 instead of capturing")
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {"frequency_hz": args.frequency, "sample_rate_hz": RATE,
              "gain_db": GAIN, "rtl_agc": False, "captures": {}}
    sync_iq = args.output_dir / "orc_sync.u8"
    cli_iq = args.output_dir / "rtl_sdr_cli.u8"
    if args.reuse_sync:
        if not sync_iq.is_file():
            parser.error(f"Existing capture missing: {sync_iq}")
        print(f"Reusing {sync_iq}", flush=True)
        report["captures"]["orc_sync"] = {"reused": True}
    else:
        print("Capturing with ORC synchronous reads...", flush=True)
        report["captures"]["orc_sync"] = capture(
            sync_iq, args.frequency, GAIN, args.seconds, False)
    if not args.skip_cli:
        print("Capturing with rtl_sdr CLI...", flush=True)
        report["captures"]["rtl_sdr_cli"] = cli_capture(
            cli_iq, args.frequency, args.seconds)
    captures = [("orc_sync", sync_iq)]
    if not args.skip_cli:
        captures.append(("rtl_sdr_cli", cli_iq))
    for name, path in captures:
        print(f"Inspecting IQ for {name}...", flush=True)
        report["captures"][name]["iq_analysis"] = inspect_iq(path)
        print(f"Decoding WAV for {name}...", flush=True)
        report["captures"][name]["audio"] = demodulate(
            path, args.output_dir / f"{name}.wav")
        (args.output_dir / "capture_comparison.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Finished {name}", flush=True)
    report_path = args.output_dir / "capture_comparison.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("Both captures are sequential and use the same ORC audio demodulator.")
    print("rtl_sdr uses librtlsdr asynchronous reads; check its stderr for lost samples.")
    print("IQ steps are a heuristic, not proof of corruption.")


if __name__ == "__main__":
    main()
