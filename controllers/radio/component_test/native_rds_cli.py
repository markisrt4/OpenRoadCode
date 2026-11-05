# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Standalone live RTL-SDR RDS diagnostics (no audio or GUI required).

Example:
  python -m controllers.radio.component_test.native_rds_cli --frequency 104300000 --seconds 60
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict

from controllers.radio.dsp.digital_downconverter import DigitalDownconverter
from controllers.radio.rds_receiver_controller import RdsReceiverController
from hardware_io.sdr.rtl_sdr_source import RtlSdrSource


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", type=int, default=104_300_000)
    parser.add_argument("--gain", type=float, default=30.0)
    parser.add_argument("--tuner-agc", action="store_true")
    parser.add_argument("--device-index", type=int, default=0)
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--report-seconds", type=float, default=5.0)
    parser.add_argument("--rf-warmup-seconds", type=float, default=2.0)
    parser.add_argument("--output", choices=("text", "json"), default="text",
                        help="human-readable status or machine-readable JSON")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def configuration(args: argparse.Namespace, parser: argparse.ArgumentParser) -> dict:
    if not 24_000_000 <= args.frequency <= 1_766_000_000:
        parser.error("frequency must be within the RTL-SDR tuner range")
    if args.seconds <= 0 or args.report_seconds <= 0 or args.rf_warmup_seconds < 0:
        parser.error("seconds/report-seconds must be positive; warmup cannot be negative")
    if args.device_index < 0:
        parser.error("device-index must be nonnegative")
    return {
        "frequency_hz": args.frequency,
        "sample_rate_hz": 2_400_000,
        "gain_db": None if args.tuner_agc else args.gain,
        "device_index": args.device_index,
        "rf_warmup_seconds": args.rf_warmup_seconds,
        "audio": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = configuration(args, parser)
    if args.output == "json":
        print(json.dumps(config, indent=2), flush=True)
    else:
        print(f"OpenRoadCode | RDS Receiver | {args.frequency / 1e6:.1f} MHz | "
              f"gain={config['gain_db']} dB | audio=off", flush=True)
    if args.dry_run:
        return 0

    source = RtlSdrSource(device_index=args.device_index, acquisition_mode="async")
    downconverter = DigitalDownconverter()
    receiver = RdsReceiverController()
    started = False
    previous_drops = 0
    blocks = 0
    total_groups = 0
    last_groups = 0
    last_metadata = receiver.status.metadata
    last_locked_phase = None
    report_groups = 0
    report_time = None
    dsp_seconds = 0.0
    exit_code = 0
    try:
        source.open()
        source.set_sample_rate(2_400_000)
        source.set_gain(config["gain_db"])
        source.set_center_frequency(args.frequency)
        source.start()
        started = True
        target = round(args.rf_warmup_seconds * 2_400_000)
        warmed = 0
        while warmed < target:
            warmed += len(source.read_iq().samples) // 2
        downconverter.reset()
        receiver.reset()
        previous_drops = source.get_acquisition_stats()["dropped_blocks"]
        start = time.monotonic()
        report_at = start + args.report_seconds
        report_time = start
        while time.monotonic() - start < args.seconds:
            block = source.read_iq()
            stats = source.get_acquisition_stats()
            drops = stats["dropped_blocks"]
            if drops > previous_drops:
                downconverter.reset()
                receiver.reset()
                print(json.dumps({"event": "source_gap", "new_drops": drops - previous_drops}), flush=True)
            previous_drops = drops
            dsp_start = time.perf_counter()
            channel_iq = downconverter.process(block, args.frequency)
            groups = receiver.process_iq(channel_iq)
            dsp_seconds += time.perf_counter() - dsp_start
            blocks += 1
            total_groups += len(groups)
            report_groups += len(groups)
            status = receiver.status
            if status.locked_pair_phase != last_locked_phase:
                event = ("SYNC ACQUIRED (phase " + str(status.locked_pair_phase) + ")"
                         if status.locked_pair_phase is not None else "SYNC LOST")
                if args.output == "text":
                    print(f"[RDS] {event}", flush=True)
                else:
                    print(json.dumps({"event": "sync_change", "message": event}), flush=True)
                last_locked_phase = status.locked_pair_phase
            if status.metadata != last_metadata:
                if args.output == "text":
                    pi = (f"0x{status.metadata.pi:04X} (unconfirmed)"
                          if status.metadata.pi is not None else "Searching...")
                    print(f"[RDS] PI: {pi} | PS: {status.metadata.program_service or 'Searching...'}"
                          f" | RT: {status.metadata.radio_text or 'Waiting...'}", flush=True)
                else:
                    print(json.dumps({"event": "metadata", **asdict(status.metadata)}), flush=True)
                last_metadata = status.metadata
            now = time.monotonic()
            if now >= report_at:
                elapsed = max(now - start, 1e-9)
                if args.output == "json":
                    print(json.dumps({
                    "elapsed_s": round(elapsed, 2),
                    "processed_blocks": blocks,
                    "groups_total": total_groups,
                    "groups_per_second": round(total_groups / elapsed, 3),
                    "rds": asdict(status),
                    "source": stats,
                    "dsp_seconds_total": round(dsp_seconds, 3),
                    "dsp_utilization": round(dsp_seconds / elapsed, 3),
                    }), flush=True)
                else:
                    pi = (f"0x{status.metadata.pi:04X} (unconfirmed)"
                          if status.metadata.pi is not None else "Searching...")
                    print(
                        f"\n=== RDS | {args.frequency / 1e6:.1f} MHz | {elapsed:.1f}s ===\n"
                        f"Sync: {'LOCKED phase ' + str(status.locked_pair_phase) if status.locked_pair_phase is not None else 'SEARCHING'}"
                        f" | PI: {pi}\n"
                        f"Station: {status.metadata.program_service or 'Searching...'}\n"
                        f"RadioText: {status.metadata.radio_text or 'Waiting...'}\n"
                        f"Groups: {total_groups} total | {report_groups / max(now - report_time, 1e-9):.2f}/s recent\n"
                        f"Invalid pairs: {status.invalid_pairs} | Carrier offset: {status.carrier_offset_hz:+.2f} Hz\n"
                        f"DSP: {100 * dsp_seconds / elapsed:.1f}% | SDR drops: {drops}",
                        flush=True,
                    )
                report_groups = 0
                report_time = now
                report_at = now + args.report_seconds
    except KeyboardInterrupt:
        print("Interrupted; stopping RDS diagnostics.", flush=True)
    except Exception as exc:
        print(f"RDS diagnostics error: {exc}", flush=True)
        exit_code = 1
    finally:
        if started:
            source.stop()
        if source.is_connected():
            source.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
