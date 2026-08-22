# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Command-line entry point for the OpenRoadCode ZeroMQ broker."""

from __future__ import annotations

import argparse

from messaging.zeromq.broker import ZeroMqBroker


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the OpenRoadCode ZeroMQ broker")
    parser.add_argument(
        "--publisher-endpoint",
        default="tcp://0.0.0.0:5556",
        help="endpoint publishers connect to",
    )
    parser.add_argument(
        "--subscriber-endpoint",
        default="tcp://0.0.0.0:5557",
        help="endpoint subscribers connect to",
    )
    args = parser.parse_args()

    broker = ZeroMqBroker(args.publisher_endpoint, args.subscriber_endpoint)
    print("OpenRoadCode ZeroMQ broker")
    print(f"  publishers  -> {args.publisher_endpoint}")
    print(f"  subscribers <- {args.subscriber_endpoint}")
    print("Ctrl+C to stop")
    try:
        broker.run()
    except KeyboardInterrupt:
        pass
    finally:
        broker.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
