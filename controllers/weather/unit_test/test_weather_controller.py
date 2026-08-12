# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for persisted Open-Meteo snapshots."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from controllers.cache import PersistentCache
from controllers.weather import (
    OpenMeteoWeatherController,
    WeatherLocation,
    WeatherSnapshotCache,
)


class WeatherControllerTest(unittest.TestCase):
    def test_refresh_persists_snapshot_for_another_instance(self) -> None:
        with TemporaryDirectory() as directory:
            response = Mock()
            response.json.return_value = {
                "current": {},
                "hourly": {},
                "daily": {},
            }
            session = Mock()
            session.get.return_value = response
            storage = PersistentCache(Path(directory))
            cache = WeatherSnapshotCache(storage)
            controller = OpenMeteoWeatherController(
                cache,
                session=session,
                clock=lambda: 100.0,
            )

            snapshot = controller.refresh()
            restored = WeatherSnapshotCache(
                PersistentCache(Path(directory))
            ).load()

            self.assertEqual(100.0, snapshot.fetched_at)
            self.assertEqual(snapshot, restored)
            response.raise_for_status.assert_called_once_with()

    def test_refresh_uses_location_provider(self) -> None:
        response = Mock()
        response.json.return_value = {
            "current": {},
            "hourly": {},
            "daily": {},
        }
        session = Mock()
        session.get.return_value = response
        provider = Mock()
        provider.get_location.return_value = WeatherLocation(
            latitude=45.0,
            longitude=-75.0,
            name="GPS fix",
            source="GPSD",
        )
        controller = OpenMeteoWeatherController(
            WeatherSnapshotCache(Mock()),
            session=session,
            location_provider=provider,
        )

        snapshot = controller.refresh()

        self.assertEqual(45.0, snapshot.latitude)
        self.assertEqual(-75.0, snapshot.longitude)
        self.assertEqual(45.0, session.get.call_args.kwargs["params"]["latitude"])

    def test_stale_snapshot_is_returned_when_refresh_fails(self) -> None:
        storage = Mock()
        cache = WeatherSnapshotCache(storage)
        existing = {
            "latitude": 1.0,
            "longitude": 2.0,
            "location_name": "Cached",
            "source": "cache",
            "fetched_at": 1.0,
            "forecast": {"current": {}, "hourly": {}, "daily": {}},
        }
        import json
        storage.get.return_value = json.dumps(existing).encode()
        session = Mock()
        session.get.side_effect = RuntimeError("offline")
        controller = OpenMeteoWeatherController(
            cache,
            session=session,
            clock=lambda: 1000.0,
        )

        snapshot = controller.refresh_if_stale(10)

        self.assertEqual("Cached", snapshot.location_name)


if __name__ == "__main__":
    unittest.main()
