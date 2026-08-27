# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.route_guidance import ReroutePolicy
from controllers.route_guidance.route_guidance_types import RouteGuidanceState


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _state(*, off_route: bool, route_complete: bool = False) -> RouteGuidanceState:
    return RouteGuidanceState(
        distance_along_route_miles=1.0,
        distance_remaining_miles=2.0,
        distance_from_route_miles=0.1 if off_route else 0.0,
        current_maneuver_index=None,
        current_maneuver=None,
        distance_to_maneuver_miles=None,
        off_route=off_route,
        route_complete=route_complete,
    )


def test_requires_sustained_off_route_condition() -> None:
    clock = _Clock()
    policy = ReroutePolicy(off_route_delay_s=3.0, clock=clock)

    assert not policy.update(_state(off_route=True))
    clock.advance(2.9)
    assert not policy.update(_state(off_route=True))
    clock.advance(0.1)
    assert policy.update(_state(off_route=True))


def test_returning_on_route_resets_delay() -> None:
    clock = _Clock()
    policy = ReroutePolicy(off_route_delay_s=3.0, clock=clock)

    assert not policy.update(_state(off_route=True))
    clock.advance(2.0)
    assert not policy.update(_state(off_route=False))
    clock.advance(2.0)
    assert not policy.update(_state(off_route=True))
    clock.advance(1.1)
    assert not policy.update(_state(off_route=True))


def test_pending_reroute_is_not_requested_twice() -> None:
    clock = _Clock()
    policy = ReroutePolicy(off_route_delay_s=0.0, clock=clock)

    assert policy.update(_state(off_route=True))
    clock.advance(20.0)
    assert not policy.update(_state(off_route=True))


def test_completed_reroute_resets_pending_and_off_route_timer() -> None:
    clock = _Clock()
    policy = ReroutePolicy(off_route_delay_s=0.0, cooldown_s=10.0, clock=clock)

    assert policy.update(_state(off_route=True))
    policy.reroute_completed()
    clock.advance(10.0)
    assert policy.update(_state(off_route=True))


def test_failed_reroute_respects_cooldown_before_retry() -> None:
    clock = _Clock()
    policy = ReroutePolicy(off_route_delay_s=0.0, cooldown_s=10.0, clock=clock)

    assert policy.update(_state(off_route=True))
    policy.reroute_failed()
    clock.advance(9.9)
    assert not policy.update(_state(off_route=True))
    clock.advance(0.1)
    assert policy.update(_state(off_route=True))


def test_arrival_never_requests_reroute() -> None:
    clock = _Clock()
    policy = ReroutePolicy(off_route_delay_s=0.0, clock=clock)

    assert not policy.update(_state(off_route=True, route_complete=True))
