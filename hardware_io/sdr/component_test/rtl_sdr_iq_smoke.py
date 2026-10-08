# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Hardware smoke test for native RTL-SDR IQ acquisition."""

from __future__ import annotations

import argparse

from hardware_io.sdr import RtlSdrSource


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", type=int, default=104_300_000)
    parser.add_argument("--sample-rate", type=int, default=2_400_000)
    parser.add_argument("--blocks", type=int, default=3)
    parser.add_argument("--gain", type=float)
    args = parser.parse_args()

    source = RtlSdrSource()
    try:
        source.open()
        source.set_sample_rate(args.sample_rate)
        source.set_center_frequency(args.frequency)
        source.set_gain(args.gain)
        source.start()

        print(
            f"RTL-SDR open: frequency={source.get_center_frequency()} Hz "
            f"sample_rate={source.get_sample_rate()} sps gain={args.gain}"
        )
        for index in range(1, args.blocks + 1):
            block = source.read_iq()
            samples = block.samples
            print(
                f"block={index} bytes={len(samples)} min={min(samples)} "
                f"max={max(samples)} unique={len(set(samples))} "
                f"first16={samples[:16].hex(' ')} timestamp_ns={block.timestamp_ns}"
            )
    finally:
        source.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
