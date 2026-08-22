# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ZeroMQ XSUB/XPUB broker for the OpenRoadCode message bus."""

from __future__ import annotations

import zmq

from messaging.zeromq.endpoints import (
    BROKER_PUBLISHER_BIND_ENDPOINT,
    BROKER_SUBSCRIBER_BIND_ENDPOINT,
)


class ZeroMqBroker:
    """Fan messages from many publishers out to many subscribers."""

    def __init__(
        self,
        publisher_endpoint: str = BROKER_PUBLISHER_BIND_ENDPOINT,
        subscriber_endpoint: str = BROKER_SUBSCRIBER_BIND_ENDPOINT,
    ) -> None:
        self._context = zmq.Context()
        self._xsub = self._context.socket(zmq.XSUB)
        self._xpub = self._context.socket(zmq.XPUB)
        self._closed = False
        try:
            self._xsub.bind(publisher_endpoint)
            self._xpub.bind(subscriber_endpoint)
        except Exception:
            self.close()
            raise

    def run(self) -> None:
        """Run the forwarding proxy until interrupted or the context stops."""
        if self._closed:
            raise RuntimeError("broker is closed")
        try:
            zmq.proxy(self._xsub, self._xpub)
        except zmq.ContextTerminated:
            pass

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._xsub.close(linger=0)
        self._xpub.close(linger=0)
        self._context.term()
