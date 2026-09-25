# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Inspect live navigation attitude and IMU telemetry from the ORC message bus."""

from __future__ import annotations

import argparse
import math
import time

from common.telemetry.navigation_bus_state import NavigationBusSnapshot, NavigationBusState
from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    IMU_STATE_TOPIC,
    decode_attitude_state,
    decode_imu_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT


def _build_dispatcher(endpoint: str, state: NavigationBusState) -> MessageDispatcher:
    from messaging.zeromq.subscriber import ZeroMqSubscriber

    dispatcher = MessageDispatcher(
        ZeroMqSubscriber(endpoint),
        error_handler=state.set_error,
    )
    dispatcher.register(ATTITUDE_STATE_TOPIC, decode_attitude_state, state.set_attitude)
    dispatcher.register(IMU_STATE_TOPIC, decode_imu_state, state.set_imu)
    return dispatcher


def _fmt(value: float | None, *, width: int = 8, precision: int = 2) -> str:
    if value is None:
        return "-".rjust(width)
    return f"{value:{width}.{precision}f}"


def _vector(vector) -> str:
    if vector is None:
        return "x=       -  y=       -  z=       -"
    return (
        f"x={_fmt(vector.x)}  y={_fmt(vector.y)}  z={_fmt(vector.z)}"
    )


def _age_ms(snapshot: NavigationBusSnapshot) -> float | None:
    if snapshot.timestamp is None:
        return None
    age = time.time() - snapshot.timestamp.timestamp()
    return max(0.0, age * 1000.0)


def _rate(count: int, previous_count: int, elapsed_s: float) -> float:
    if elapsed_s <= 0.0:
        return 0.0
    return (count - previous_count) / elapsed_s


def _render(
    snapshot: NavigationBusSnapshot,
    *,
    attitude_rate_hz: float,
    imu_rate_hz: float,
    clear: bool,
) -> None:
    if clear:
        print("\033[2J\033[H", end="")

    age = _age_ms(snapshot)
    age_text = "-" if age is None else f"{age:.0f} ms"
    connected = "YES" if snapshot.connected else "NO"

    print("OpenRoadCode Live Navigation Sensor Component Test")
    print("=" * 52)
    print(f"connected:          {connected}")
    print(f"last update age:    {age_text}")
    if snapshot.error:
        print(f"error:              {snapshot.error}")
    print()
    print(
        f"attitude messages:  {snapshot.attitude_count:8d}   "
        f"rate: {attitude_rate_hz:6.1f} Hz   source: {snapshot.attitude_source or '-'}"
    )
    print(
        f"IMU messages:       {snapshot.imu_count:8d}   "
        f"rate: {imu_rate_hz:6.1f} Hz   source: {snapshot.imu_source or '-'}"
    )
    print()
    print(f"heading:            {_fmt(snapshot.heading_deg)} deg")
    print(f"pitch:              {_fmt(snapshot.pitch_deg)} deg")
    print(f"roll:               {_fmt(snapshot.roll_deg)} deg")
    print()
    print(f"acceleration:       {_vector(snapshot.acceleration_mps2)}  m/s^2")
    print(f"linear acceleration:{_vector(snapshot.linear_acceleration_mps2)}  m/s^2")
    print(f"angular velocity:   {_vector(snapshot.angular_velocity_rad_s)}  rad/s")
    print()
    print("Move/tilt the sensor device. Ctrl-C exits.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Subscribe to live ORC attitude/IMU telemetry and display message "
            "sources, rates, attitude, and raw sensor vectors."
        )
    )
    parser.add_argument("--endpoint", default=LOCAL_SUBSCRIBER_ENDPOINT)
    parser.add_argument(
        "--refresh",
        type=float,
        default=0.5,
        help="display refresh interval in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="print successive samples instead of refreshing the terminal",
    )
    args = parser.parse_args()
    if not math.isfinite(args.refresh) or args.refresh <= 0.0:
        parser.error("--refresh must be a finite value greater than zero")
    return args


def main() -> int:
    args = parse_args()
    state = NavigationBusState()
    dispatcher = _build_dispatcher(args.endpoint, state)
    dispatcher.start()

    previous_attitude_count = 0
    previous_imu_count = 0
    previous_sample_time = time.monotonic()

    try:
        while True:
            time.sleep(args.refresh)
            now = time.monotonic()
            elapsed_s = now - previous_sample_time
            snapshot = state.snapshot()
            attitude_rate_hz = _rate(
                snapshot.attitude_count,
                previous_attitude_count,
                elapsed_s,
            )
            imu_rate_hz = _rate(
                snapshot.imu_count,
                previous_imu_count,
                elapsed_s,
            )
            _render(
                snapshot,
                attitude_rate_hz=attitude_rate_hz,
                imu_rate_hz=imu_rate_hz,
                clear=not args.no_clear,
            )
            previous_attitude_count = snapshot.attitude_count
            previous_imu_count = snapshot.imu_count
            previous_sample_time = now
    except KeyboardInterrupt:
        print("\nSensor component test stopped.")
        return 0
    finally:
        dispatcher.close()


if __name__ == "__main__":
    raise SystemExit(main())
