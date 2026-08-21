# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Print public OpenRoadCode vehicle telemetry received over ZeroMQ."""

import argparse
import json

import zmq

from telemetry.topics import VEHICLE_STATE_TOPIC


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="tcp://127.0.0.1:5556")
    args = parser.parse_args()

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(args.endpoint)
    socket.setsockopt_string(zmq.SUBSCRIBE, VEHICLE_STATE_TOPIC)

    try:
        while True:
            topic = socket.recv_string()
            payload = socket.recv_json()
            print(f"{topic} {json.dumps(payload, sort_keys=True)}")
    except KeyboardInterrupt:
        pass
    finally:
        socket.close(linger=0)
        context.term()


if __name__ == "__main__":
    main()
