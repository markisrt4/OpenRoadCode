# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import math
import unittest
from datetime import datetime, timezone

from apps.common.navigation_map_follow import NavigationMapFollowRuntime
from controllers.navigation.navigation_state import GroundMotionState, PositionState
from messaging.contracts.navigation import (
    decode_motion_state,
    decode_position_state,
    encode_motion_state,
    encode_position_state,
)


class RecordingAdapter:
    def __init__(self) -> None:
        self.positions: list[PositionState] = []
        self.motions: list[GroundMotionState] = []
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def update(self, state: PositionState) -> None:
        self.positions.append(state)

    def update_ground_motion(self, state: GroundMotionState) -> None:
        self.motions.append(state)


class DummySubscriber:
    def subscribe(self, _topic: str) -> None:
        pass

    def receive(self, timeout_ms: int | None = None):
        return None

    def close(self) -> None:
        pass


class NavigationMapFollowRuntimeTest(unittest.TestCase):
    def test_dispatches_position_and_motion_to_existing_adapter(self) -> None:
        adapter = RecordingAdapter()
        runtime = NavigationMapFollowRuntime(
            DummySubscriber(),  # type: ignore[arg-type]
            adapter,  # type: ignore[arg-type]
        )
        position = PositionState(
            received_at=datetime(2026, 8, 24, tzinfo=timezone.utc),
            latitude_deg=42.8028,
            longitude_deg=-83.0127,
            altitude_m=250.0,
            fix_mode=3,
            satellites_visible=12,
            satellites_used=9,
            accuracy_m=2.5,
            source="simulation",
        )
        position_message = decode_position_state(encode_position_state(position))
        motion_message = decode_motion_state(
            encode_motion_state(
                timestamp={"seconds": 1_777_000_000, "nanoseconds": 0},
                source="simulation",
                ground_speed_m_s=13.4,
                course_rad=math.radians(91.0),
            )
        )

        runtime._handle_position(position_message)  # noqa: SLF001
        runtime._handle_motion(motion_message)  # noqa: SLF001

        self.assertEqual(1, len(adapter.positions))
        state = adapter.positions[0]
        self.assertAlmostEqual(42.8028, state.latitude_deg or 0.0)
        self.assertAlmostEqual(-83.0127, state.longitude_deg or 0.0)
        self.assertEqual("simulation", state.source)
        self.assertEqual(3, state.fix_mode)

        self.assertEqual(1, len(adapter.motions))
        motion = adapter.motions[0]
        self.assertAlmostEqual(13.4, motion.speed_mps or 0.0)
        self.assertTrue(math.isclose(91.0, motion.course_deg or 0.0))
        self.assertEqual("simulation", motion.source)


if __name__ == "__main__":
    unittest.main()
