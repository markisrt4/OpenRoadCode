# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ZeroMQ XSUB/XPUB broker for the OpenRoadCode message bus."""

from __future__ import annotations

import zmq


class ZeroMqBroker:
    """Fan messages from many publishers out to many subscribers.

    Publishers connect to ``publisher_endpoint``. Subscribers connect to
    ``subscriber_endpoint``. The broker performs no OpenRoadCode decoding or
    contract validation; it only proxies ZeroMQ multipart messages and
    subscription events.
    """

    def __init__(
        self,
        publisher_endpoint: str = "tcp://0.0.0.0:5556",
        subscriber_endpoint: str = "tcp://0.0.0.0:5557",
    ) -> None:
        self._context = zmq.Context()
        self._xsub = self._context.socket(zmq.XSUB)
        self._xpub = self._context.socket(zmq.XPUB)
        self._xsub.bind(publisher_endpoint)
        self._xpub.bind(subscriber_endpoint)
        self._closed = False

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
        self._xsub.close(linger=0)
        self._xpub.close(linger=0)
        self._context.term()
        self._closed = True
