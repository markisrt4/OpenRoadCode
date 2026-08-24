# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Diagnose vehicle-state delivery through MessageDispatcher."""

from __future__ import annotations

import argparse
import time

from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, decode_vehicle_state
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=LOCAL_SUBSCRIBER_ENDPOINT)
    args = parser.parse_args()

    received = 0

    def handle_vehicle(message) -> None:
        nonlocal received
        received += 1
        data = message.data
        print(
            f"dispatch #{received}: source={message.source} "
            f"engine_speed_rad_s={data.engine_speed_rad_s} "
            f"vehicle_speed_m_s={data.vehicle_speed_m_s}"
        )

    def handle_error(topic: str, error: Exception) -> None:
        print(f"ERROR [{topic}]: {type(error).__name__}: {error}")

    dispatcher = MessageDispatcher(
        ZeroMqSubscriber(args.endpoint),
        error_handler=handle_error,
    )
    dispatcher.register(
        VEHICLE_STATE_TOPIC,
        decode_vehicle_state,
        handle_vehicle,
    )
    dispatcher.start()

    print("OpenRoadCode vehicle-state dispatcher diagnostic")
    print(f"  endpoint: {args.endpoint}")
    print(f"  topic:    {VEHICLE_STATE_TOPIC}")
    print("Ctrl+C to stop")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        dispatcher.close()


if __name__ == "__main__":
    main()
