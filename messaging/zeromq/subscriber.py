# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ZeroMQ implementation of the OpenRoadCode subscriber interface."""

from collections.abc import Mapping
from typing import Any

import zmq

from messaging.subscriber_if import SubscriberIf


class ZeroMqSubscriber(SubscriberIf):
    """Receive topic-prefixed JSON messages using a ZeroMQ SUB socket."""

    def __init__(self, endpoint: str = "tcp://127.0.0.1:5556") -> None:
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.SUB)
        self._socket.connect(endpoint)
        self._closed = False

    def subscribe(self, topic: str) -> None:
        if self._closed:
            raise RuntimeError("subscriber is closed")
        self._socket.setsockopt_string(zmq.SUBSCRIBE, topic)

    def receive(self) -> tuple[str, Mapping[str, Any]]:
        if self._closed:
            raise RuntimeError("subscriber is closed")
        topic = self._socket.recv_string()
        payload = self._socket.recv_json()
        if not isinstance(payload, dict):
            raise ValueError("OpenRoadCode JSON message payload must be an object")
        return topic, payload

    def close(self) -> None:
        if self._closed:
            return
        self._socket.close(linger=0)
        self._context.term()
        self._closed = True
