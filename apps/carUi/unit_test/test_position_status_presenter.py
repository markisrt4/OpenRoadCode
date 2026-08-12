# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for provider-independent position presentation."""

import unittest

from apps.carUi.position_status_presenter import PositionStatusPresenter
from controllers.navigation import PositionState


class FakePositionSource:
    def __init__(self) -> None:
        self.callback = None
        self.starts = 0
        self.stops = 0

    def start(self, callback) -> None:
        self.starts += 1
        self.callback = callback

    def stop(self) -> None:
        self.stops += 1

    def publish(self, state: PositionState) -> None:
        assert self.callback is not None
        self.callback(state)


class PositionStatusPresenterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = FakePositionSource()
        self.positions: list[tuple[float | None, float | None]] = []
        self.statuses: list[str] = []
        self.dispatched = 0
        self.position_states: list[PositionState] = []

        def dispatch(callback) -> None:
            self.dispatched += 1
            callback()

        self.presenter = PositionStatusPresenter(
            source=self.source,  # type: ignore[arg-type]
            dispatch=dispatch,
            set_position=lambda lat, lon: self.positions.append((lat, lon)),
            set_status=self.statuses.append,
            on_position_state=self.position_states.append,
        )

    def test_presents_gpsd_fix_on_dispatcher(self) -> None:
        self.presenter.start()
        self.source.publish(
            PositionState(
                latitude_deg=42.1,
                longitude_deg=-83.2,
                fix_mode=3,
                satellites_used=7,
                satellites_visible=10,
                source="gpsd",
            )
        )

        self.assertEqual(self.dispatched, 1)
        self.assertEqual(self.positions, [(42.1, -83.2)])
        self.assertEqual(len(self.position_states), 1)
        self.assertEqual(self.statuses[-1], "GPS acquired: 7/10 satellites")

    def test_no_fix_clears_displayed_position(self) -> None:
        self.presenter.start()
        self.source.publish(PositionState(source="gpsd"))

        self.assertEqual(self.positions, [(None, None)])
        self.assertEqual(self.statuses[-1], "Position unavailable")

    def test_cached_fix_is_visibly_identified(self) -> None:
        self.presenter.start()
        self.source.publish(
            PositionState(
                latitude_deg=42.1,
                longitude_deg=-83.2,
                fix_mode=3,
                source="gpsd",
                is_cached=True,
            )
        )

        self.assertEqual(self.positions[-1], (42.1, -83.2))
        self.assertEqual(
            self.statuses[-1],
            "Last known position restored; waiting for a live fix",
        )

    def test_start_and_stop_are_idempotent(self) -> None:
        self.presenter.start()
        self.presenter.start()
        self.presenter.stop()
        self.presenter.stop()

        self.assertEqual(self.source.starts, 1)
        self.assertEqual(self.source.stops, 1)


if __name__ == "__main__":
    unittest.main()
