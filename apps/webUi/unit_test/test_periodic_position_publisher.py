# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from datetime import datetime, timezone

import pytest

from apps.webUi.periodic_position_publisher import PeriodicPositionPublisher
from controllers.navigation.navigation_state import PositionState


def _state(latitude: float = 42.0) -> PositionState:
    return PositionState(
        received_at=datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
        latitude_deg=latitude,
        longitude_deg=-83.0,
        speed_mps=10.0,
        fix_mode=3,
        source="browser",
    )


def test_rejects_non_positive_rate() -> None:
    with pytest.raises(ValueError):
        PeriodicPositionPublisher(lambda state: None, rate_hz=0.0)


def test_publish_without_position_does_nothing() -> None:
    published = []
    publisher = PeriodicPositionPublisher(published.append)

    assert publisher.publish_once() is False
    assert published == []


def test_new_fix_is_fresh_then_cached() -> None:
    published = []
    publisher = PeriodicPositionPublisher(published.append)
    publisher.update(_state())

    assert publisher.publish_once() is True
    assert publisher.publish_once() is True

    assert published[0].is_cached is False
    assert published[1].is_cached is True


def test_new_fix_resets_cached_state() -> None:
    published = []
    publisher = PeriodicPositionPublisher(published.append)
    publisher.update(_state(42.0))
    publisher.publish_once()
    publisher.publish_once()

    publisher.update(_state(43.0))
    publisher.publish_once()
    publisher.publish_once()

    assert [state.is_cached for state in published] == [False, True, False, True]
    assert published[2].latitude_deg == 43.0


def test_update_does_not_mutate_input_cache_flag() -> None:
    published = []
    publisher = PeriodicPositionPublisher(published.append)
    state = _state()

    publisher.update(state)
    publisher.publish_once()

    assert state.is_cached is False
    assert published[0] is not state
