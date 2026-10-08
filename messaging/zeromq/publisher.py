# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from collections.abc import Mapping
from typing import Any
from threading import Lock
import json

import zmq

from messaging.publisher_if import PublisherIf
from messaging.zeromq.endpoints import LOCAL_PUBLISHER_ENDPOINT


class ZeroMqPublisher(PublisherIf):
    """ZeroMQ publisher that connects to the OpenRoadCode broker ingress."""

    def __init__(self, endpoint: str = LOCAL_PUBLISHER_ENDPOINT) -> None:
        self._lock = Lock()
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.PUB)
        self._socket.connect(endpoint)
        self._closed = False

    def publish(self, topic: str, payload: Mapping[str, Any]) -> None:
        frames = [topic.encode("utf-8"), json.dumps(dict(payload)).encode("utf-8")]
        # Navigation workers and UI controls share publishers. Serialize all
        # socket access, including the complete multipart message and shutdown.
        with self._lock:
            if self._closed:
                raise RuntimeError("publisher is closed")
            self._socket.send_multipart(frames)

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._socket.close(linger=0)
                self._context.term()
                self._closed = True
