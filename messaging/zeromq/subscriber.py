# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ZeroMQ implementation of the OpenRoadCode subscriber interface."""

from __future__ import annotations

from collections.abc import Mapping
from threading import Event, Lock, get_ident
from typing import Any

import zmq

from messaging.subscriber_if import SubscriberIf
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT


class ZeroMqSubscriber(SubscriberIf):
    """Receive topic-prefixed JSON messages using a thread-owned SUB socket.

    Topic subscriptions may be registered before reception starts. The actual
    ZeroMQ context and socket are created lazily by the thread that first calls
    :meth:`receive`, preserving ZeroMQ socket thread affinity.
    """

    _POLL_TIMEOUT_MS = 100

    def __init__(self, endpoint: str = LOCAL_SUBSCRIBER_ENDPOINT) -> None:
        self._endpoint = endpoint
        self._topics: list[str] = []
        self._topics_lock = Lock()
        self._close_event = Event()
        self._context: zmq.Context | None = None
        self._socket: zmq.Socket | None = None
        self._owner_thread_id: int | None = None

    def subscribe(self, topic: str) -> None:
        if self._close_event.is_set():
            raise RuntimeError("subscriber is closed")
        if not topic:
            raise ValueError("topic must not be empty")

        with self._topics_lock:
            if self._socket is not None:
                raise RuntimeError(
                    "subscriptions must be registered before receive() starts"
                )
            if topic not in self._topics:
                self._topics.append(topic)

    def receive(self) -> tuple[str, Mapping[str, Any]]:
        if self._close_event.is_set():
            self._cleanup_if_owner()
            raise RuntimeError("subscriber is closed")

        self._ensure_transport()
        assert self._socket is not None

        while not self._close_event.is_set():
            if not self._socket.poll(self._POLL_TIMEOUT_MS, zmq.POLLIN):
                continue

            topic = self._socket.recv_string()
            payload = self._socket.recv_json()
            if not isinstance(payload, dict):
                raise ValueError(
                    "OpenRoadCode JSON message payload must be an object"
                )
            return topic, payload

        self._cleanup_if_owner()
        raise RuntimeError("subscriber is closed")

    def close(self) -> None:
        self._close_event.set()
        # If close() is called by the socket-owning thread (for example the
        # simple blocking subscriber CLI), resources can be released now.
        # Otherwise receive() will notice the close event within one poll
        # interval and clean up on its owning thread.
        self._cleanup_if_owner()

    def _ensure_transport(self) -> None:
        current_thread_id = get_ident()
        if self._socket is not None:
            if self._owner_thread_id != current_thread_id:
                raise RuntimeError(
                    "ZeroMQ subscriber receive() called from multiple threads"
                )
            return

        self._owner_thread_id = current_thread_id
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.SUB)
        self._socket.connect(self._endpoint)

        with self._topics_lock:
            topics = tuple(self._topics)
        for topic in topics:
            self._socket.setsockopt_string(zmq.SUBSCRIBE, topic)

    def _cleanup_if_owner(self) -> None:
        if self._socket is None:
            return
        if self._owner_thread_id != get_ident():
            return

        self._socket.close(linger=0)
        self._socket = None

        if self._context is not None:
            self._context.term()
            self._context = None

        self._owner_thread_id = None
