# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Receive and decode public navigation position messages."""

from dataclasses import asdict
import json

from messaging.contracts.navigation import POSITION_STATE_TOPIC, decode_position_state
from messaging.zeromq import ZeroMqSubscriber


def main() -> None:
    subscriber = ZeroMqSubscriber()
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
