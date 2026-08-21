from collections.abc import Mapping
from typing import Any
import zmq
from messaging.publisher_if import PublisherIf

class ZeroMqPublisher(PublisherIf):
    def __init__(self, endpoint: str = "tcp://127.0.0.1:5556") -> None:
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.PUB)
        self._socket.bind(endpoint)
        self._closed = False

    def publish(self, topic: str, payload: Mapping[str, Any]) -> None:
        if self._closed:
            raise RuntimeError("publisher is closed")
        self._socket.send_string(topic, zmq.SNDMORE)
        self._socket.send_json(dict(payload))

    def close(self) -> None:
        if not self._closed:
            self._socket.close(linger=0)
            self._context.term()
            self._closed = True
