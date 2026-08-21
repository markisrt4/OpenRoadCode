# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ZeroMQ implementation of the OpenRoadCode telemetry publisher."""

from collections.abc import Mapping

import zmq

from .publisher_if import TelemetryPublisherIf


class ZeroMqTelemetryPublisher(TelemetryPublisherIf):
    """Publish topic-prefixed JSON telemetry using a ZeroMQ PUB socket."""

    def __init__(self, endpoint: str = "tcp://127.0.0.1:5556") -> None:
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.PUB)
        self._socket.bind(endpoint)
        self._closed = False

    def publish(self, topic: str, payload: Mapping[str, object]) -> None:
        if self._closed:
            raise RuntimeError("telemetry publisher is closed")
        self._socket.send_string(topic, zmq.SNDMORE)
        self._socket.send_json(dict(payload))

    def close(self) -> None:
        if self._closed:
            return
        self._socket.close(linger=0)
        self._context.term()
        self._closed = True
