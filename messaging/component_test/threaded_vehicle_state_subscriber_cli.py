# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Diagnose ZeroMQ vehicle-state reception from a background thread."""

from __future__ import annotations

import threading
import time

from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, decode_vehicle_state
from messaging.zeromq import ZeroMqSubscriber


def main() -> None:
    stop_event = threading.Event()

    def receive_loop() -> None:
        subscriber = ZeroMqSubscriber()
        subscriber.subscribe(VEHICLE_STATE_TOPIC)
        print("receiver thread: subscriber created and topic registered", flush=True)
        count = 0
        try:
            while not stop_event.is_set():
                topic, payload = subscriber.receive()
                message = decode_vehicle_state(payload)
                count += 1
                print(
                    f"threaded receive #{count}: topic={topic} source={message.source}",
                    flush=True,
                )
        except Exception as exc:
            if not stop_event.is_set():
                print(
                    f"receiver thread ERROR: {type(exc).__name__}: {exc}",
                    flush=True,
                )
        finally:
            subscriber.close()
            print("receiver thread: stopped", flush=True)

    thread = threading.Thread(
        target=receive_loop,
        name="openroad-threaded-zmq-diagnostic",
        daemon=True,
    )
    thread.start()

    print("OpenRoadCode threaded vehicle-state subscriber diagnostic")
    print("Ctrl+C to stop")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        thread.join(timeout=1.0)


if __name__ == "__main__":
    main()
