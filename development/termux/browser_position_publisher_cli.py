# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish browser geolocation fixes onto the OpenRoadCode navigation bus."""

from __future__ import annotations

import argparse
import signal
import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.carUi.runtime.browser_position_source import BrowserPositionSource
from messaging.contracts.navigation import PositionStatePublisher
from messaging.zeromq.publisher import ZeroMqPublisher


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--publisher-endpoint",
        default="tcp://127.0.0.1:5556",
        help="OpenRoadCode broker ingress endpoint",
    )
    args = parser.parse_args()

    publisher = ZeroMqPublisher(args.publisher_endpoint)
    position_publisher = PositionStatePublisher(publisher)
    source = BrowserPositionSource(host=args.host, port=args.port)
    stopped = threading.Event()

    def handle_position(state) -> None:
        position_publisher.publish(state)
        print(
            "[browser-gps] "
            f"lat={state.latitude_deg:.6f} "
            f"lon={state.longitude_deg:.6f} "
            f"accuracy={state.accuracy_m}m"
        )

    def handle_shutdown_signal(signum: int, _frame: object) -> None:
        print(f"\n[browser-gps] received signal {signum}; shutting down")
        stopped.set()

    previous_handlers: dict[int, object] = {}
    for signum in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, handle_shutdown_signal)

    try:
        source.start(handle_position)
        print(f"[browser-gps] publishing to {args.publisher_endpoint}")
        print("[browser-gps] press Ctrl+C to stop")
        stopped.wait()
    finally:
        source.stop()
        publisher.close()
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        print("[browser-gps] stopped")


if __name__ == "__main__":
    main()
