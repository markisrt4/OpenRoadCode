#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Live PipeWire music-analysis smoke test."""
from __future__ import annotations

import argparse
import time

from controllers.audio.capture import PipewireAudioCapture
from controllers.audio.music_analysis import MusicAnalyzer, MusicAnalysisState
from controllers.audio.music_analysis.music_analysis_pipeline import MusicAnalysisPipeline


def _format_state(state: MusicAnalysisState) -> str:
    percussion = state.percussion
    return (
        f"level={state.level:.3f} "
        f"bass={state.bass:.3f} mid={state.mid:.3f} treble={state.treble:.3f} "
        f"kick={percussion.kick:.3f} snare={percussion.snare:.3f} "
        f"cymbal={percussion.cymbal:.3f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture live PipeWire PCM and run the OpenRoadCode music analyzer.",
    )
    parser.add_argument(
        "--target",
        help="optional PipeWire target node name or id; omit to use pw-record's default",
    )
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--sample-rate", type=int, default=48_000)
    parser.add_argument("--fft-size", type=int, default=2048)
    parser.add_argument(
        "--print-every",
        type=int,
        default=10,
        help="print every N analyzed blocks",
    )
    args = parser.parse_args()

    if args.seconds <= 0.0:
        parser.error("--seconds must be positive")
    if args.print_every <= 0:
        parser.error("--print-every must be positive")

    capture = PipewireAudioCapture(
        sample_rate_hz=args.sample_rate,
        block_size=args.fft_size,
        target=args.target,
    )
    analyzer = MusicAnalyzer(fft_size=args.fft_size)

    block_count = 0

    def on_analysis(state: MusicAnalysisState) -> None:
        nonlocal block_count
        block_count += 1
        if block_count == 1 or block_count % args.print_every == 0:
            print(f"{block_count:5d}: {_format_state(state)}", flush=True)

    pipeline = MusicAnalysisPipeline(capture, analyzer, on_analysis)

    print("Starting live PipeWire music analysis...")
    print(f"target:      {args.target or '<pw-record default>'}")
    print(f"sample rate: {args.sample_rate} Hz")
    print(f"FFT size:    {args.fft_size}")
    print(f"duration:    {args.seconds:.1f} s")

    try:
        pipeline.start()
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline and pipeline.is_running:
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("Interrupted.")
    finally:
        pipeline.stop()

    if block_count == 0:
        print("No complete audio blocks were captured.")
        return 2

    print(f"Captured and analyzed {block_count} block(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
