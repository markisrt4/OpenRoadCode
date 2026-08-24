# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import time
from datetime import datetime, timezone

from controllers.navigation.navigation_state import PositionState
from controllers.route_guidance import RouteGuidanceController
from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteManeuver,
    RouteResult,
)
from messaging.contracts.navigation import POSITION_STATE_TOPIC, encode_position_state
from apps.common.route_guidance_runtime import RouteGuidanceRuntime


class _Subscriber:
    def __init__(self) -> None:
        self.callback = None

    def subscribe(self, topic: str) -> None:
        self.topic = topic

    def receive(self, timeout_ms: int | None = None):
        if self.callback is None:
            time.sleep(0.01)
            return None
        item = self.callback
        self.callback = None
        return item

    def close(self) -> None:
        pass


class _GuidancePublisher:
    def __init__(self) -> None:
        self.states = []

    def publish(self, state) -> None:
        self.states.append(state)


def _route() -> RouteResult:
    return RouteResult(
        1.0,
        120.0,
        (
            GeoPoint(42.0000, -83.0000),
            GeoPoint(42.0000, -82.9900),
            GeoPoint(42.0100, -82.9900),
        ),
        (
            RouteManeuver("Head east", None, 0.5, 60.0, 0, 1),
            RouteManeuver("Turn left", None, 0.5, 60.0, 1, 2),
        ),
    )


def _position_payload(latitude: float | None, longitude: float | None):
    return encode_position_state(
        PositionState(
            received_at=datetime.now(timezone.utc),
            latitude_deg=latitude,
            longitude_deg=longitude,
            altitude_m=None,
            speed_mps=10.0,
            course_deg=90.0,
            fix_mode=3,
            source="test",
        )
    )


def test_valid_position_updates_guidance() -> None:
    subscriber = _Subscriber()
    publisher = _GuidancePublisher()
    runtime = RouteGuidanceRuntime(
        subscriber,
        RouteGuidanceController(_route()),
        publisher,
    )

    # Exercise the registered handler directly; MessageDispatcher itself has
    # separate tests, while this test owns conversion + guidance + publication.
    runtime._handle_position(  # noqa: SLF001
        __import__(
            "messaging.contracts.navigation",
            fromlist=["decode_position_state"],
        ).decode_position_state(_position_payload(42.0000, -82.9950))
    )

    assert len(publisher.states) == 1
    assert publisher.states[0].current_maneuver_index == 0
    assert not publisher.states[0].off_route


def test_missing_coordinates_are_ignored() -> None:
    subscriber = _Subscriber()
    publisher = _GuidancePublisher()
    runtime = RouteGuidanceRuntime(
        subscriber,
        RouteGuidanceController(_route()),
        publisher,
    )

    runtime._handle_position(  # noqa: SLF001
        __import__(
            "messaging.contracts.navigation",
            fromlist=["decode_position_state"],
        ).decode_position_state(_position_payload(None, None))
    )

    assert publisher.states == []
