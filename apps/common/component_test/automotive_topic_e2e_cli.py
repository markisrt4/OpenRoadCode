#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Verify configured OBD-II telemetry through the application consumer path."""

from __future__ import annotations

import argparse
import sys
import threading
from dataclasses import asdict
from pathlib import Path

from common.telemetry.vehicle_bus_state import VehicleBusState
from config.service_runtime_config import ServiceRuntimeConfigParser
from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, decode_vehicle_state
from messaging.message_dispatcher import MessageDispatcher
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

    delivered = threading.Event()
    consumer = VehicleBusState()

    def receive_vehicle(message) -> None:
        consumer.set_vehicle(message)
        delivered.set()

    def receive_error(topic: str, error: Exception) -> None:
        consumer.set_error(topic, error)
        delivered.set()

    dispatcher = MessageDispatcher(
        ZeroMqSubscriber(system.messaging.subscriber_endpoint),
        error_handler=receive_error,
    )
    dispatcher.register(VEHICLE_STATE_TOPIC, decode_vehicle_state, receive_vehicle)
    dispatcher.start()

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

    runtime_thread = threading.Thread(target=run_automotive, name="AutomotiveE2eRuntime", daemon=True)
    runtime_thread.start()

    try:
        if not delivered.wait(args.topic_timeout):
            print(
                f"FAIL [consumer]: no {VEHICLE_STATE_TOPIC} application snapshot arrived "
                f"within {args.topic_timeout:g} seconds",
                file=sys.stderr,
            )
            return 5
        if runtime_error:
            print(f"FAIL [automotive runtime]: {runtime_error[0]}", file=sys.stderr)
            return 3

        snapshot = consumer.snapshot()
        if snapshot.error is not None:
            print(f"FAIL [consumer]: {snapshot.error}", file=sys.stderr)
            return 5
        if not snapshot.connected or snapshot.state is None:
            print("FAIL [consumer]: no connected vehicle snapshot", file=sys.stderr)
            return 5

        values = {
            name: value
            for name, value in asdict(snapshot.state).items()
            if name != "timestamp"
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        }
        print(f"PASS [topic]: {VEHICLE_STATE_TOPIC}")
        print(f"PASS [consumer]: {snapshot.status}")
        print(f"  timestamp: {snapshot.state.timestamp.isoformat()}")
        for name, value in sorted(values.items()):
            print(f"  {name}: {value}")
        if not values:
            print("FAIL [payload]: snapshot contained no numeric vehicle values", file=sys.stderr)
            return 6
        print(f"PASS [application]: decoded {len(values)} vehicle value(s) end to end")
        return 0
    finally:
        runtime.close()
        runtime_thread.join(timeout=config.input.timeout_s * 16 + 5.0)
        dispatcher.close()
        publisher.close()


if __name__ == "__main__":
    raise SystemExit(main())
