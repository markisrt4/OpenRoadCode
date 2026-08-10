"""Tests for live and cached weather location selection."""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock

from apps.carUi.runtime.weather_location_provider import (
    CarUiWeatherLocationProvider,
)
from controllers.navigation import PositionState
from controllers.weather import WeatherLocation


class WeatherLocationProviderTest(unittest.TestCase):
    def test_live_gpsd_location_takes_precedence(self) -> None:
        gpsd = Mock()
        expected = WeatherLocation(42.0, -83.0, "GPS", "GPSD")
        gpsd.get_location.return_value = expected
        cache = Mock()
        provider = CarUiWeatherLocationProvider(gpsd, cache)

        self.assertIs(expected, provider.get_location())
        cache.load.assert_not_called()

    def test_recent_cached_position_is_weather_fallback(self) -> None:
        gpsd = Mock()
        gpsd.get_location.side_effect = RuntimeError("no fix")
        cache = Mock()
        cache.load.return_value = PositionState(
            received_at=datetime.now() - timedelta(minutes=5),
            latitude_deg=42.1,
            longitude_deg=-83.2,
            fix_mode=3,
            is_cached=True,
        )
        provider = CarUiWeatherLocationProvider(gpsd, cache)

        location = provider.get_location()

        self.assertEqual(42.1, location.latitude)
        self.assertEqual("Last known position", location.source)


if __name__ == "__main__":
    unittest.main()
