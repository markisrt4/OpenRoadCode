# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Command-line entry point for the OpenRoadCode ZeroMQ broker."""

from __future__ import annotations

import argparse

import zmq

from messaging.zeromq.broker import ZeroMqBroker
from messaging.zeromq.endpoints import (
    BROKER_PUBLISHER_BIND_ENDPOINT,
    BROKER_SUBSCRIBER_BIND_ENDPOINT,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the OpenRoadCode ZeroMQ broker")
    parser.add_argument(
        "--publisher-endpoint",
        default=BROKER_PUBLISHER_BIND_ENDPOINT,
        help="endpoint publishers connect to",
    )
    parser.add_argument(
        "--subscriber-endpoint",
        default=BROKER_SUBSCRIBER_BIND_ENDPOINT,
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
    except zmq.ZMQError as error:
        if error.errno == zmq.EADDRINUSE:
            print("ZeroMQ broker is already running on the configured endpoints")
            return 0
        raise
    finally:
        broker.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
