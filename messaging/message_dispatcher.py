# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Transport-independent topic decoding and handler dispatch."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import CancelledError, Executor, ThreadPoolExecutor
from dataclasses import dataclass
from threading import Event, Lock, Thread
from typing import Any

from messaging.subscriber_if import SubscriberIf

Decoder = Callable[[Mapping[str, Any]], Any]
Handler = Callable[[Any], None]
ErrorHandler = Callable[[str, Exception], None]


@dataclass(frozen=True, slots=True)
class _Registration:
    decoder: Decoder
    handler: Handler


class MessageDispatcher:
    """Receive subscribed messages and dispatch decoded objects to handlers.

    Exactly one receiver thread owns the SubscriberIf. Handler execution is
    delegated to a shared Executor so slow consumers do not block reception.
    Register all topics before calling start(). Handlers run on executor worker
    threads and therefore must not directly mutate thread-affine UI toolkits.
    """

    def __init__(
        self,
        subscriber: SubscriberIf,
        *,
        executor: Executor | None = None,
        max_workers: int = 4,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        """Create a dispatcher around one transport subscriber.

        @param subscriber Transport-independent subscriber owned by the receive loop.
        @param executor Optional executor used for decoded message handlers.
        @param max_workers Worker count used when the dispatcher creates its executor.
        @param error_handler Optional callback receiving topic and dispatch exceptions.
        """
        if max_workers <= 0:
            raise ValueError("max_workers must be greater than zero")
        self._subscriber = subscriber
        self._executor = executor or ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="openroad-dispatch",
        )
        self._owns_executor = executor is None
        self._error_handler = error_handler
        self._registrations: dict[str, _Registration] = {}
        self._lock = Lock()
        self._stop_event = Event()
        self._thread = Thread(
            target=self._receive_loop,
            name="openroad-message-receiver",
            daemon=True,
        )
        self._started = False
        self._closed = False

    def register(self, topic: str, decoder: Decoder, handler: Handler) -> None:
        """Subscribe and register one decoder/handler pair for a topic."""
        if not topic:
            raise ValueError("topic must not be empty")
        with self._lock:
            if self._started:
                raise RuntimeError("registrations must be completed before start()")
            if self._closed:
                raise RuntimeError("dispatcher is closed")
            if topic in self._registrations:
                raise ValueError(f"topic already registered: {topic}")
            self._registrations[topic] = _Registration(decoder, handler)
        self._subscriber.subscribe(topic)

    def start(self) -> None:
        """Start the single subscriber receive thread after registration is complete."""
        with self._lock:
            if self._closed:
                raise RuntimeError("dispatcher is closed")
            if self._started:
                return
            self._started = True
        self._thread.start()

    def close(self) -> None:
        """Stop reception before shutting down handler workers.

        The receive thread must be fully stopped before the owned executor is
        shut down. Otherwise a message received during teardown can race an
        executor shutdown and attempt to submit work after shutdown has begun.
        """
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._stop_event.set()
        self._subscriber.close()
        if self._thread.is_alive():
            self._thread.join()
        if self._owns_executor:
            self._executor.shutdown(wait=True, cancel_futures=True)

    def _receive_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                topic, payload = self._subscriber.receive()
            except Exception as exc:
                if not self._stop_event.is_set():
                    self._report_error("receive", exc)
                return

            # close() can become visible while receive() is returning. Do not
            # decode or submit one final message after shutdown has started.
            if self._stop_event.is_set():
                return

            with self._lock:
                registration = self._registrations.get(topic)
            if registration is None:
                continue

            try:
                message = registration.decoder(payload)
            except Exception as exc:
                if not self._stop_event.is_set():
                    self._report_error(topic, exc)
                continue

            if self._stop_event.is_set():
                return

            try:
                future = self._executor.submit(registration.handler, message)
            except RuntimeError as exc:
                # An externally supplied executor can be shut down independently.
                # During our own teardown this is expected and should be silent.
                if not self._stop_event.is_set():
                    self._report_error(topic, exc)
                return
            future.add_done_callback(
                lambda completed, message_topic=topic: self._handler_done(
                    message_topic, completed
                )
            )

    def _handler_done(self, topic: str, future) -> None:
        if future.cancelled():
            return
        try:
            future.result()
        except CancelledError:
            return
        except Exception as exc:
            if not self._stop_event.is_set():
                self._report_error(topic, exc)

    def _report_error(self, topic: str, exc: Exception) -> None:
        if self._error_handler is not None:
            self._error_handler(topic, exc)
