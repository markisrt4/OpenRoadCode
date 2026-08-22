# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ZeroMQ XSUB/XPUB broker for the OpenRoadCode message bus."""

from __future__ import annotations

from threading import Event

import zmq

from messaging.zeromq.endpoints import (
    BROKER_PUBLISHER_BIND_ENDPOINT,
    BROKER_SUBSCRIBER_BIND_ENDPOINT,
)


class ZeroMqBroker:
    """Fan messages from many publishers out to many subscribers."""

    _POLL_TIMEOUT_MS = 100

    def __init__(
        self,
        publisher_endpoint: str = BROKER_PUBLISHER_BIND_ENDPOINT,
        subscriber_endpoint: str = BROKER_SUBSCRIBER_BIND_ENDPOINT,
    ) -> None:
        self._publisher_endpoint = publisher_endpoint
        self._subscriber_endpoint = subscriber_endpoint
        self._stop_event = Event()
        self._running = Event()

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    def run(self) -> None:
        """Run the forwarding broker until :meth:`close` requests shutdown.

        The ZeroMQ context and sockets are created and destroyed on this thread
        so callers may safely run the broker in either the foreground or a
        dedicated Python thread.
        """
        if self._stop_event.is_set():
            raise RuntimeError("broker is closed")
        if self._running.is_set():
            raise RuntimeError("broker is already running")

        context = zmq.Context()
        xsub = context.socket(zmq.XSUB)
        xpub = context.socket(zmq.XPUB)
        try:
            xsub.bind(self._publisher_endpoint)
            xpub.bind(self._subscriber_endpoint)
            self._running.set()

            poller = zmq.Poller()
            poller.register(xsub, zmq.POLLIN)
            poller.register(xpub, zmq.POLLIN)

            while not self._stop_event.is_set():
                events = dict(poller.poll(self._POLL_TIMEOUT_MS))

                if xsub in events:
                    # Publisher traffic is multipart: topic + JSON payload.
                    xpub.send_multipart(xsub.recv_multipart())

                if xpub in events:
                    # XPUB emits subscription/unsubscription frames which must
                    # travel back to XSUB so upstream publishers receive them.
                    xsub.send(xpub.recv())
        finally:
            self._running.clear()
            xsub.close(linger=0)
            xpub.close(linger=0)
            context.term()

    def close(self) -> None:
        """Request broker shutdown without touching another thread's sockets."""
        self._stop_event.set()
