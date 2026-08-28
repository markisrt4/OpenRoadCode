#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Verify physical OBD-II telemetry across the automotive ZeroMQ topic."""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from controllers.automotive.obd2 import Elm327ObdAdapter, Obd2Manager
from hardware_io.automotive.elm327 import Elm327Device
from messaging.contracts.automotive import (
    VEHICLE_STATE_TOPIC,
    decode_vehicle_state,
)
from messaging.zeromq import ZeroMqPublisher, ZeroMqSubscriber
from messaging.zeromq.broker import ZeroMqBroker
from services.automotive.automotive_runtime import AutomotiveRuntime


def _free_tcp_endpoint() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return f"tcp://127.0.0.1:{sock.getsockname()[1]}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/rfcomm0")
    parser.add_argument("--baud", type=int, default=38400)
    parser.add_argument("--serial-timeout", type=float, default=1.0)
    parser.add_argument("--topic-timeout", type=float, default=45.0)
    args = parser.parse_args()
    if args.serial_timeout <= 0 or args.serial_timeout > 10:
        parser.error("--serial-timeout must be greater than 0 and at most 10 seconds")
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
    if not Path(args.port).exists():
        print(f"FAIL [RFCOMM]: {args.port} does not exist", file=sys.stderr)
        return 2

    ingress = _free_tcp_endpoint()
    egress = _free_tcp_endpoint()
    while egress == ingress:
        egress = _free_tcp_endpoint()

    broker = ZeroMqBroker(ingress, egress)
    broker_thread = threading.Thread(target=broker.run, name="Obd2E2eBroker", daemon=True)
    broker_thread.start()
    deadline = time.monotonic() + 2.0
    while not broker.is_running and time.monotonic() < deadline:
        time.sleep(0.01)
    if not broker.is_running:
        print("FAIL [broker]: local ZeroMQ broker did not start", file=sys.stderr)
        return 4

    subscriber = ZeroMqSubscriber(egress)
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

    source = Obd2Manager(
        Elm327ObdAdapter(
            Elm327Device(
                port=args.port,
                baud=args.baud,
                timeout=args.serial_timeout,
            )
        )
    )
    publisher = ZeroMqPublisher(ingress)
    runtime = AutomotiveRuntime(source, publisher, publish_source="obd2-e2e", rate_hz=1.0)
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
        runtime_thread.join(timeout=args.serial_timeout * 16 + 5.0)
        subscriber.close()
        receiver_thread.join(timeout=1.0)
        publisher.close()
        broker.close()
        broker_thread.join(timeout=2.0)


if __name__ == "__main__":
    raise SystemExit(main())
