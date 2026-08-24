# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import queue
import threading
import unittest
from collections.abc import Mapping
from typing import Any

from messaging.message_dispatcher import MessageDispatcher
from messaging.subscriber_if import SubscriberIf


class FakeSubscriber(SubscriberIf):
    def __init__(self) -> None:
        self.subscriptions: list[str] = []
        self.messages: queue.Queue[tuple[str, Mapping[str, Any]] | None] = queue.Queue()
        self.closed = False

    def subscribe(self, topic_prefix: str) -> None:
        self.subscriptions.append(topic_prefix)

    def receive(self) -> tuple[str, Mapping[str, Any]]:
        item = self.messages.get(timeout=1.0)
        if item is None:
            raise RuntimeError("subscriber closed")
        return item

    def close(self) -> None:
        self.closed = True
        self.messages.put(None)

    def push(self, topic: str, payload: Mapping[str, Any]) -> None:
        self.messages.put((topic, payload))


class MessageDispatcherTest(unittest.TestCase):
    def test_register_subscribes_topic(self) -> None:
        subscriber = FakeSubscriber()
        dispatcher = MessageDispatcher(subscriber)
        try:
            dispatcher.register("topic.one", lambda payload: payload, lambda message: None)
            self.assertEqual(["topic.one"], subscriber.subscriptions)
        finally:
            dispatcher.close()

    def test_duplicate_topic_is_rejected(self) -> None:
        subscriber = FakeSubscriber()
        dispatcher = MessageDispatcher(subscriber)
        try:
            dispatcher.register("topic.one", lambda payload: payload, lambda message: None)
            with self.assertRaises(ValueError):
                dispatcher.register("topic.one", lambda payload: payload, lambda message: None)
        finally:
            dispatcher.close()

    def test_registration_after_start_is_rejected(self) -> None:
        subscriber = FakeSubscriber()
        dispatcher = MessageDispatcher(subscriber)
        dispatcher.start()
        try:
            with self.assertRaises(RuntimeError):
                dispatcher.register("topic.one", lambda payload: payload, lambda message: None)
        finally:
            dispatcher.close()

    def test_message_is_decoded_and_dispatched(self) -> None:
        subscriber = FakeSubscriber()
        received: list[int] = []
        handled = threading.Event()

        def decoder(payload: Mapping[str, Any]) -> int:
            return int(payload["value"]) * 2

        def handler(message: int) -> None:
            received.append(message)
            handled.set()

        dispatcher = MessageDispatcher(subscriber)
        dispatcher.register("topic.one", decoder, handler)
        dispatcher.start()
        try:
            subscriber.push("topic.one", {"value": 21})
            self.assertTrue(handled.wait(timeout=1.0))
            self.assertEqual([42], received)
        finally:
            dispatcher.close()

    def test_decoder_error_is_reported_without_handler_call(self) -> None:
        subscriber = FakeSubscriber()
        errors: list[tuple[str, str]] = []
        handler_called = threading.Event()
        error_seen = threading.Event()

        def decoder(payload: Mapping[str, Any]) -> object:
            raise ValueError("bad payload")

        def on_error(topic: str, error: Exception) -> None:
            errors.append((topic, str(error)))
            error_seen.set()

        dispatcher = MessageDispatcher(subscriber, error_handler=on_error)
        dispatcher.register("topic.one", decoder, lambda message: handler_called.set())
        dispatcher.start()
        try:
            subscriber.push("topic.one", {"value": 1})
            self.assertTrue(error_seen.wait(timeout=1.0))
            self.assertFalse(handler_called.is_set())
            self.assertEqual([("topic.one", "bad payload")], errors)
        finally:
            dispatcher.close()

    def test_handler_error_is_reported(self) -> None:
        subscriber = FakeSubscriber()
        errors: list[tuple[str, str]] = []
        error_seen = threading.Event()

        def handler(message: object) -> None:
            raise RuntimeError("handler failed")

        def on_error(topic: str, error: Exception) -> None:
            errors.append((topic, str(error)))
            error_seen.set()

        dispatcher = MessageDispatcher(subscriber, error_handler=on_error)
        dispatcher.register("topic.one", lambda payload: payload, handler)
        dispatcher.start()
        try:
            subscriber.push("topic.one", {"value": 1})
            self.assertTrue(error_seen.wait(timeout=1.0))
            self.assertEqual([("topic.one", "handler failed")], errors)
        finally:
            dispatcher.close()

    def test_close_closes_subscriber(self) -> None:
        subscriber = FakeSubscriber()
        dispatcher = MessageDispatcher(subscriber)
        dispatcher.start()
        dispatcher.close()
        self.assertTrue(subscriber.closed)


if __name__ == "__main__":
    unittest.main()
