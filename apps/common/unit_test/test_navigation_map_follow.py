# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import math
import time
import unittest
from datetime import datetime, timezone

from apps.common.navigation_map_follow import NavigationMapFollowRuntime
from controllers.navigation.navigation_state import PositionState
from messaging.contracts.navigation import (
    POSITION_STATE_TOPIC,
    encode_position_state,
)
from messaging.subscriber_if import SubscriberIf


class QueueSubscriber(SubscriberIf):
    def __init__(self) -> None:
        self.topic: str | None = None
        self.payload = None
        self.closed = False

    def subscribe(self, topic: str) -> None:
        self.topic = topic

    def receive(self):
        deadline = time.monotonic() + 1.0
        while self.payload is None and not self.closed:
            if time.monotonic() >= deadline:
                raise RuntimeError("test subscriber timed out")
            time.sleep(0.001)
        if self.closed:
            raise RuntimeError("subscriber is closed")
        payload = self.payload
        self.payload = None
        return self.topic, payload

    def close(self) -> None:
        self.closed = True


class RecordingAdapter:
    def __init__(self) -> None:
        self.states: list[PositionState] = []
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def update(self, state: PositionState) -> None:
        self.states.append(state)


class NavigationMapFollowRuntimeTest(unittest.TestCase):
    def test_dispatches_position_contract_to_existing_adapter(self) -> None:
        subscriber = QueueSubscriber()
        adapter = RecordingAdapter()
        runtime = NavigationMapFollowRuntime(
            subscriber,
            adapter,  # type: ignore[arg-type]
        )
        subscriber.payload = encode_position_state(
            PositionState(
                received_at=datetime(2026, 8, 24, tzinfo=timezone.utc),
                latitude_deg=42.8028,
                longitude_deg=-83.0127,
                altitude_m=250.0,
                speed_mps=13.4,
                course_deg=91.0,
                fix_mode=3,
                satellites_visible=12,
                satellites_used=9,
                accuracy_m=2.5,
                source="simulation",
            )
        )

        runtime.start()
        deadline = time.monotonic() + 1.0
        while not adapter.states and time.monotonic() < deadline:
            time.sleep(0.001)
        runtime.close()

        self.assertTrue(adapter.started)
        self.assertTrue(adapter.stopped)
        self.assertEqual(POSITION_STATE_TOPIC, subscriber.topic)
        self.assertEqual(1, len(adapter.states))
        state = adapter.states[0]
        self.assertAlmostEqual(42.8028, state.latitude_deg or 0.0)
        self.assertAlmostEqual(-83.0127, state.longitude_deg or 0.0)
        self.assertAlmostEqual(13.4, state.speed_mps or 0.0)
        self.assertTrue(math.isclose(91.0, state.course_deg or 0.0))
        self.assertEqual("simulation", state.source)
        self.assertEqual(3, state.fix_mode)


if __name__ == "__main__":
    unittest.main()
