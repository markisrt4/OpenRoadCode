# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for persisted last-known position behavior."""

import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from controllers.cache import PersistentCache
from controllers.navigation import (
    PersistentPositionSource,
    PositionSnapshotCache,
    PositionState,
)


class FakePositionSource:
    def __init__(self) -> None:
        self.callback = None
        self.stopped = False

    def start(self, callback) -> None:
        self.callback = callback

    def stop(self) -> None:
        self.stopped = True

    def publish(self, state: PositionState) -> None:
        assert self.callback is not None
        self.callback(state)


class PersistentPositionSourceTest(unittest.TestCase):
    def test_cached_fix_is_published_before_live_source(self) -> None:
        now = datetime(2026, 8, 9, 12, 0, 0)
        with TemporaryDirectory() as directory:
            cache = PositionSnapshotCache(PersistentCache(Path(directory)))
            cache.store(
                PositionState(
                    received_at=now - timedelta(minutes=5),
                    latitude_deg=42.1,
                    longitude_deg=-83.2,
                    fix_mode=3,
                    source="gpsd",
                )
            )
            live = FakePositionSource()
            states: list[PositionState] = []
            source = PersistentPositionSource(
                live,
                cache,
                max_age_seconds=600,
                clock=lambda: now,
            )

            source.start(states.append)

            self.assertEqual(1, len(states))
            self.assertTrue(states[0].is_cached)
            self.assertEqual(states[0].latitude_deg, 42.1)
            self.assertEqual(states[0].longitude_deg, -83.2)

    def test_no_fix_does_not_replace_last_good_position(self) -> None:
        now = datetime(2026, 8, 9, 12, 0, 0)
        with TemporaryDirectory() as directory:
            cache = PositionSnapshotCache(PersistentCache(Path(directory)))
            live = FakePositionSource()
            source = PersistentPositionSource(live, cache, clock=lambda: now)
            source.start(lambda _state: None)
            good = PositionState(
                received_at=now,
                latitude_deg=42.1,
                longitude_deg=-83.2,
                fix_mode=3,
                source="browser",
            )
            live.publish(good)
            live.publish(PositionState(source="browser"))

            restored = cache.load()

            self.assertIsNotNone(restored)
            self.assertEqual(42.1, restored.latitude_deg)  # type: ignore[union-attr]

    def test_live_fixes_are_forwarded_while_cache_writes_are_throttled(self) -> None:
        now = datetime(2026, 8, 9, 12, 0, 0)
        current_time = [now]
        cache = Mock()
        cache.load.return_value = None
        live = FakePositionSource()
        states: list[PositionState] = []
        source = PersistentPositionSource(
            live,
            cache,
            persist_interval_seconds=15.0,
            clock=lambda: current_time[0],
        )
        source.start(states.append)

        def publish(latitude: float) -> None:
            live.publish(
                PositionState(
                    received_at=current_time[0],
                    latitude_deg=latitude,
                    longitude_deg=-83.2,
                    fix_mode=3,
                    source="browser",
                )
            )

        publish(42.1)
        current_time[0] += timedelta(seconds=5)
        publish(42.2)
        current_time[0] += timedelta(seconds=10)
        publish(42.3)

        self.assertEqual(3, len(states))
        self.assertEqual(2, cache.store.call_count)
        self.assertEqual(42.1, cache.store.call_args_list[0].args[0].latitude_deg)
        self.assertEqual(42.3, cache.store.call_args_list[1].args[0].latitude_deg)

    def test_expired_fix_is_not_published(self) -> None:
        now = datetime(2026, 8, 9, 12, 0, 0)
        cache = Mock()
        cache.load.return_value = PositionState(
            received_at=now - timedelta(days=2),
            latitude_deg=42.1,
            longitude_deg=-83.2,
            fix_mode=3,
            is_cached=True,
        )
        states: list[PositionState] = []
        source = PersistentPositionSource(
            FakePositionSource(),
            cache,
            max_age_seconds=3600,
            clock=lambda: now,
        )

        source.start(states.append)

        self.assertEqual([], states)

    def test_negative_persist_interval_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "persist_interval_seconds"):
            PersistentPositionSource(
                FakePositionSource(),
                Mock(),
                persist_interval_seconds=-1.0,
            )


if __name__ == "__main__":
    unittest.main()
