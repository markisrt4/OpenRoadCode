#!/usr/bin/env python3
"""Hardware-independent ORC RigCTL smoke-test CLI.

Example: python -m protocols.rigctl.component_test.rigctl_smoke_cli --port 4532
"""
from __future__ import annotations

import argparse
from protocols.rigctl.rigctl_client import RigctlClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a RigCTL receiver from OpenRoadCode")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4532)
    parser.add_argument("--frequency", type=int, help="Optional frequency in Hz to tune")
    parser.add_argument("--mode", choices=["FM", "NFM", "WFM", "AM"])
    parser.add_argument("--bandwidth", type=int, default=0)
    parser.add_argument("--start", action="store_true")
    parser.add_argument("--stop", action="store_true")
    args = parser.parse_args()
    client = RigctlClient(args.host, args.port)
    try:
        if args.start:
            print("start:", client.start())
        if args.mode:
            print("mode:", client.set_mode(args.mode, args.bandwidth))
        if args.frequency is not None:
            print("tune:", client.set_frequency(args.frequency))
        frequency = client.get_frequency()
        print("frequency_hz:", frequency)
        if not frequency.isdecimal():
            raise RuntimeError("receiver returned a non-numeric frequency")
        print("strength:", client.get_signal_strength())
        print("snr:", client.get_snr())
        print("rds:", client.get_rds())
        if args.stop:
            print("stop:", client.stop())
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(1, f"RigCTL smoke test failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
