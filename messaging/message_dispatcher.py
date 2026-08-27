# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Transport-independent topic decoding and handler dispatch."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import Executor, ThreadPoolExecutor
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

    def register(self, topic: str, decoder: Decoder, handler: Handler) -> None:
        """Subscribe and register one decoder/handler pair for a topic.

        @param topic Public topic name to subscribe to and dispatch.
        @param decoder Contract decoder that converts the wire payload to a typed message.
        @param handler Application callback invoked with each decoded message.
        """
        if not topic:
            raise ValueError("topic must not be empty")
        with self._lock:
            if self._started:
                raise RuntimeError("registrations must be completed before start()")
            if topic in self._registrations:
                raise ValueError(f"topic already registered: {topic}")
            self._registrations[topic] = _Registration(decoder, handler)
        self._subscriber.subscribe(topic)

    def start(self) -> None:
        """Start the single subscriber receive thread after registration is complete."""
        with self._lock:
            if self._started:
                return
            self._started = True
        self._thread.start()

    def close(self) -> None:
        """Stop reception, close transport resources, and drain handler work."""
        self._stop_event.set()
        self._subscriber.close()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)
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

            with self._lock:
                registration = self._registrations.get(topic)
            if registration is None:
                continue

            try:
                message = registration.decoder(payload)
            except Exception as exc:
                self._report_error(topic, exc)
                continue

            future = self._executor.submit(registration.handler, message)
            future.add_done_callback(
                lambda completed, message_topic=topic: self._handler_done(
                    message_topic, completed
                )
            )

    def _handler_done(self, topic: str, future) -> None:
        try:
            future.result()
        except Exception as exc:
            self._report_error(topic, exc)

    def _report_error(self, topic: str, exc: Exception) -> None:
        if self._error_handler is not None:
            self._error_handler(topic, exc)
