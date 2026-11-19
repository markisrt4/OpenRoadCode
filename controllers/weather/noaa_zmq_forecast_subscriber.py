# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Background ZMQ subscription for SDRForge NOAA forecast messages."""

from __future__ import annotations

import logging
from threading import Event, Lock, Thread
from typing import Any, Callable

from controllers.weather.noaa_weather_event_adapter import (
    NOAA_FORECAST_TOPIC,
    NoaaWeatherEventAdapter,
)

_LOG = logging.getLogger(__name__)


class NoaaZmqForecastSubscriber:
    """Own a ZMQ SUB socket on a worker thread; never block the weather UI."""

    def __init__(
        self,
        adapter: NoaaWeatherEventAdapter,
        *,
        endpoint: str = "tcp://127.0.0.1:5573",
        poll_timeout_ms: int = 100,
        context_factory: Callable[[], Any] | None = None,
    ) -> None:
        if poll_timeout_ms < 1:
            raise ValueError("poll_timeout_ms must be positive")
        self._adapter = adapter
        self._endpoint = endpoint
        self._poll_timeout_ms = poll_timeout_ms
        self._context_factory = context_factory
        self._stop = Event()
        self._lifecycle_lock = Lock()
        self._thread: Thread | None = None
        self.received = 0
        self.rejected = 0
        self.last_error: str | None = None

    @property
    def running(self) -> bool:
        """Return whether the subscriber worker is active."""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start or restart the subscriber worker safely."""
        with self._lifecycle_lock:
            if self.running:
                return
            self._stop.clear()
            self.last_error = None
            self._thread = Thread(target=self._run, name="orc-noaa-rf", daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Request shutdown and wait for the worker to release its socket."""
        with self._lifecycle_lock:
            self._stop.set()
            thread = self._thread
            if thread is not None:
                thread.join(timeout)
                if thread.is_alive():
                    raise RuntimeError("NOAA subscriber failed to stop")
                self._thread = None

    def _run(self) -> None:
        try:
            import zmq
        except ImportError:
            self.last_error = "pyzmq is required for NOAA RF subscriptions"
            _LOG.error(self.last_error)
            return
        socket = None
        try:
            context = (
                self._context_factory()
                if self._context_factory is not None
                else zmq.Context.instance()
            )
            socket = context.socket(zmq.SUB)
            socket.setsockopt(zmq.SUBSCRIBE, NOAA_FORECAST_TOPIC)
            socket.setsockopt(zmq.LINGER, 0)
            socket.connect(self._endpoint)
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            while not self._stop.is_set():
                if socket not in dict(poller.poll(self._poll_timeout_ms)):
                    continue
                try:
                    self._adapter.ingest_frame(socket.recv())
                except ValueError as exc:
                    self.rejected += 1
                    self.last_error = str(exc)
                    _LOG.warning("Rejected NOAA forecast frame: %s", exc)
                else:
                    self.received += 1
        except (OSError, zmq.ZMQError) as exc:
            self.last_error = str(exc)
            _LOG.warning("NOAA forecast subscriber stopped: %s", exc)
        finally:
            if socket is not None:
                socket.close(linger=0)
