# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Receive and decode public vehicle-state messages over ZeroMQ."""

from dataclasses import asdict
import json

from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, decode_vehicle_state
from messaging.zeromq import ZeroMqSubscriber


def main() -> None:
    subscriber = ZeroMqSubscriber()
    subscriber.subscribe(VEHICLE_STATE_TOPIC)

    try:
        while True:
            topic, payload = subscriber.receive()
            message = decode_vehicle_state(payload)
            print(topic)
            print(json.dumps(asdict(message), indent=2, sort_keys=True))
    except KeyboardInterrupt:
        pass
    finally:
        subscriber.close()


if __name__ == "__main__":
    main()
