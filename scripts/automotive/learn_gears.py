#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Learn forward-gear RPM/speed ratios from live OpenRoadCode telemetry.

The learner subscribes to ``openroad.vehicle.state`` and records stable
engine-speed / road-speed samples.  After enough driving data has been
collected, it clusters the samples into the requested number of forward gears
and writes a small TOML profile that can later feed a runtime gear estimator.
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from pathlib import Path
import statistics
import sys
import time

from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, decode_vehicle_state
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT

RPM_PER_RAD_S = 60.0 / (2.0 * 3.141592653589793)
MPH_PER_MPS = 2.2369362920544


@dataclass(frozen=True)
class Sample:
    rpm: float
    speed_mph: float
    rpm_per_mph: float


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Learn vehicle forward-gear ratios from ORC telemetry."
    )
    parser.add_argument("--gears", type=int, default=6, help="number of forward gears")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("vehicle_gears.learned.toml"),
        help="output TOML profile",
    )
    parser.add_argument(
        "--endpoint",
        default=LOCAL_SUBSCRIBER_ENDPOINT,
        help="ZeroMQ subscriber endpoint",
    )
    parser.add_argument(
        "--min-speed-mph",
        type=float,
        default=5.0,
        help="ignore samples below this road speed",
    )
    parser.add_argument(
        "--min-rpm",
        type=float,
        default=900.0,
        help="ignore samples below this engine speed",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=8,
        help="ratio samples used to decide whether the driveline is stable",
    )
    parser.add_argument(
        "--max-window-spread",
        type=float,
        default=0.035,
        help="maximum fractional ratio spread accepted as stable",
    )
    return parser.parse_args()


def _stable_ratio(history: deque[float], max_spread: float) -> bool:
    if len(history) < history.maxlen:
        return False
    mean = statistics.fmean(history)
    if mean <= 0.0:
        return False
    return (max(history) - min(history)) / mean <= max_spread


def _kmeans_1d(values: list[float], clusters: int) -> list[list[float]]:
    if clusters <= 0:
        raise ValueError("clusters must be positive")
    if len(values) < clusters:
        raise ValueError("not enough samples to form requested gear clusters")

    ordered = sorted(values)
    centers = [
        ordered[round(i * (len(ordered) - 1) / max(1, clusters - 1))]
        for i in range(clusters)
    ]

    assignments: list[list[float]] = [[] for _ in centers]
    for _ in range(100):
        assignments = [[] for _ in centers]
        for value in values:
            index = min(range(len(centers)), key=lambda i: abs(value - centers[i]))
            assignments[index].append(value)

        new_centers = [
            statistics.median(group) if group else centers[i]
            for i, group in enumerate(assignments)
        ]
        if max(abs(a - b) for a, b in zip(centers, new_centers)) < 1e-6:
            break
        centers = new_centers

    paired = sorted(zip(centers, assignments), key=lambda item: item[0], reverse=True)
    return [group for _center, group in paired]


def _write_profile(path: Path, groups: list[list[float]], sample_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Learned by scripts/automotive/learn_gears.py",
        f"sample_count = {sample_count}",
        f"gear_count = {len(groups)}",
        "ratio_units = \"rpm_per_mph\"",
        "",
    ]

    for gear, group in enumerate(groups, start=1):
        if not group:
            continue
        center = statistics.median(group)
        mean = statistics.fmean(group)
        spread = statistics.pstdev(group) if len(group) > 1 else 0.0
        minimum = min(group)
        maximum = max(group)
        lines.extend(
            [
                f"[[gear]]",
                f"number = {gear}",
                f"rpm_per_mph = {center:.6f}",
                f"mean_rpm_per_mph = {mean:.6f}",
                f"stddev_rpm_per_mph = {spread:.6f}",
                f"min_rpm_per_mph = {minimum:.6f}",
                f"max_rpm_per_mph = {maximum:.6f}",
                f"samples = {len(group)}",
                "",
            ]
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def _print_summary(groups: list[list[float]]) -> None:
    print("\nLearned gear ratios:")
    for gear, group in enumerate(groups, start=1):
        if not group:
            print(f"  gear {gear}: no samples")
            continue
        center = statistics.median(group)
        spread = statistics.pstdev(group) if len(group) > 1 else 0.0
        print(
            f"  gear {gear}: {center:8.2f} rpm/mph  "
            f"samples={len(group):5d}  sigma={spread:6.2f}"
        )


def main() -> int:
    args = _parse_args()
    if args.gears < 1:
        raise SystemExit("--gears must be at least 1")
    if args.window < 2:
        raise SystemExit("--window must be at least 2")

    subscriber = ZeroMqSubscriber(args.endpoint)
    subscriber.subscribe(VEHICLE_STATE_TOPIC)

    ratio_history: deque[float] = deque(maxlen=args.window)
    samples: list[Sample] = []
    last_status = 0.0

    print("OpenRoadCode gear learner")
    print(f"  telemetry:     {args.endpoint}")
    print(f"  forward gears: {args.gears}")
    print(f"  min speed:     {args.min_speed_mph:.1f} mph")
    print("Drive normally through every forward gear.")
    print("Steady in-gear cruising/acceleration is useful; shifts and clutch slip are rejected.")
    print("Press Ctrl+C when all gears have been exercised.\n")

    try:
        while True:
            topic, payload = subscriber.receive()
            if topic != VEHICLE_STATE_TOPIC:
                continue

            message = decode_vehicle_state(payload)
            engine_speed = message.data.engine_speed_rad_s
            vehicle_speed = message.data.vehicle_speed_m_s
            if engine_speed is None or vehicle_speed is None:
                ratio_history.clear()
                continue

            rpm = engine_speed * RPM_PER_RAD_S
            speed_mph = vehicle_speed * MPH_PER_MPS
            if rpm < args.min_rpm or speed_mph < args.min_speed_mph:
                ratio_history.clear()
                continue

            ratio = rpm / speed_mph
            ratio_history.append(ratio)
            if _stable_ratio(ratio_history, args.max_window_spread):
                samples.append(Sample(rpm=rpm, speed_mph=speed_mph, rpm_per_mph=ratio))

            now = time.monotonic()
            if now - last_status >= 1.0:
                state = "stable" if _stable_ratio(ratio_history, args.max_window_spread) else "reject"
                print(
                    f"\r{rpm:5.0f} rpm  {speed_mph:5.1f} mph  "
                    f"{ratio:7.2f} rpm/mph  {state:6s}  accepted={len(samples):5d}",
                    end="",
                    flush=True,
                )
                last_status = now
    except KeyboardInterrupt:
        print("\n\nStopping learner...")
    finally:
        subscriber.close()

    if len(samples) < args.gears * 5:
        print(
            f"Only {len(samples)} stable samples were collected. "
            f"Collect at least {args.gears * 5} before fitting {args.gears} gears.",
            file=sys.stderr,
        )
        return 2

    groups = _kmeans_1d([sample.rpm_per_mph for sample in samples], args.gears)
    _print_summary(groups)
    _write_profile(args.output, groups, len(samples))
    print(f"\nWrote learned profile: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
