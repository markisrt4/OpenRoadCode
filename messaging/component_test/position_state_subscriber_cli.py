# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Receive and decode public navigation position messages."""

import argparse
from dataclasses import asdict
import json

from messaging.contracts.navigation import POSITION_STATE_TOPIC, decode_position_state
from messaging.zeromq import ZeroMqSubscriber


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--endpoint",
        default="tcp://127.0.0.1:5557",
        help="ZeroMQ publisher endpoint, e.g. tcp://192.168.8.20:5557",
    )
    args = parser.parse_args()

    subscriber = ZeroMqSubscriber(args.endpoint)
    subscriber.subscribe(POSITION_STATE_TOPIC)
    try:
        while True:
            topic, payload = subscriber.receive()
            message = decode_position_state(payload)
            print(topic, json.dumps(asdict(message), indent=2, sort_keys=True))
    except KeyboardInterrupt:
        pass
    finally:
        subscriber.close()


if __name__ == "__main__":
    main()
