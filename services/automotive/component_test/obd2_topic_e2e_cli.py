#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Verify physical OBD-II telemetry across the automotive ZeroMQ topic."""

from __future__ import annotations

import argparse
import sys
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

from config.service_runtime_config import ServiceRuntimeConfigParser
from messaging.contracts.automotive import (
    VEHICLE_STATE_TOPIC,
    decode_vehicle_state,
)
from messaging.zeromq import ZeroMqPublisher, ZeroMqSubscriber
from services.automotive.automotive_runtime import AutomotiveRuntime
from services.automotive.automotive_service_cli import (
    DEFAULT_RUNTIME_CONFIG,
    build_source,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_RUNTIME_CONFIG))
    parser.add_argument("--topic-timeout", type=float, default=45.0)
    args = parser.parse_args()
    if args.topic_timeout <= 0 or args.topic_timeout > 180:
        parser.error("--topic-timeout must be greater than 0 and at most 180 seconds")
    return args


def _numeric_values(message: Any) -> dict[str, int | float]:
    return {
        name: value
        for name, value in asdict(message.data).items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }


def main() -> int:
    args = parse_args()
    system = ServiceRuntimeConfigParser(args.config).load()
    config = system.automotive
    if not config.enabled:
        print("FAIL [config]: services.automotive.enabled is false", file=sys.stderr)
        return 2
    if not config.publish.enabled:
        print("FAIL [config]: services.automotive.publish.enabled is false", file=sys.stderr)
        return 2
    if config.input.source == "device" and not Path(config.input.port).exists():
        print(f"FAIL [RFCOMM]: {config.input.port} does not exist", file=sys.stderr)
        return 2

    print(f"Config: {Path(args.config).expanduser().resolve()}")
    print(f"Input: {config.input.source}")
    if config.input.source == "device":
        print(f"Device: {config.input.device} on {config.input.port} at {config.input.baud} baud")
    print(f"Publisher endpoint: {system.messaging.publisher_endpoint}")
    print(f"Subscriber endpoint: {system.messaging.subscriber_endpoint}")

    subscriber = ZeroMqSubscriber(system.messaging.subscriber_endpoint)
    subscriber.subscribe(VEHICLE_STATE_TOPIC)
    received: list[tuple[str, Any]] = []
    receiver_error: list[Exception] = []
    delivered = threading.Event()

    def receive_one() -> None:
        try:
            topic, payload = subscriber.receive()
            received.append((topic, decode_vehicle_state(payload)))
            delivered.set()
        except Exception as exc:
            receiver_error.append(exc)
            delivered.set()

    receiver_thread = threading.Thread(target=receive_one, name="Obd2E2eSubscriber", daemon=True)
    receiver_thread.start()
    time.sleep(0.2)

    source = build_source(config)
    publisher = ZeroMqPublisher(system.messaging.publisher_endpoint)
    runtime = AutomotiveRuntime(
        source,
        publisher,
        publish_source=config.publish.source,
        rate_hz=config.rate_hz,
    )
    runtime_error: list[Exception] = []

    def run_automotive() -> None:
        try:
            runtime.run()
        except Exception as exc:
            runtime_error.append(exc)
            delivered.set()

    runtime_thread = threading.Thread(target=run_automotive, name="Obd2E2eRuntime", daemon=True)
    runtime_thread.start()

    try:
        if not delivered.wait(args.topic_timeout):
            print(
                f"FAIL [topic]: no {VEHICLE_STATE_TOPIC} message arrived within "
                f"{args.topic_timeout:g} seconds",
                file=sys.stderr,
            )
            return 5
        if runtime_error:
            print(f"FAIL [automotive runtime]: {runtime_error[0]}", file=sys.stderr)
            return 3
        if receiver_error:
            print(f"FAIL [subscriber]: {receiver_error[0]}", file=sys.stderr)
            return 5
        if not received:
            print("FAIL [topic]: subscriber completed without a message", file=sys.stderr)
            return 5

        topic, message = received[0]
        values = _numeric_values(message)
        print(f"PASS [topic]: {topic}")
        print(f"  source: {message.source}")
        print(f"  timestamp: {message.timestamp}")
        for name, value in sorted(values.items()):
            print(f"  {name}: {value}")
        if not values:
            print("FAIL [payload]: message contained no numeric vehicle values", file=sys.stderr)
            return 6
        print(f"PASS [payload]: decoded {len(values)} vehicle value(s) end to end")
        return 0
    finally:
        runtime.close()
        runtime_thread.join(timeout=config.input.timeout_s * 16 + 5.0)
        subscriber.close()
        receiver_thread.join(timeout=1.0)
        publisher.close()


if __name__ == "__main__":
    raise SystemExit(main())
