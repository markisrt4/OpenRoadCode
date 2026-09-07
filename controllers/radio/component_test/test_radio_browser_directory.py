# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
import unittest

from controllers.radio.adapters.radio_browser_directory import RadioBrowserDirectory


_RUN_NETWORK_TESTS = os.environ.get("ORC_RUN_NETWORK_COMPONENT_TESTS") == "1"


@unittest.skipUnless(
    _RUN_NETWORK_TESTS,
    "set ORC_RUN_NETWORK_COMPONENT_TESTS=1 to run live Radio Browser tests",
)
class RadioBrowserDirectoryComponentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = RadioBrowserDirectory(timeout_s=10.0)

    def test_finds_michigan_stations(self) -> None:
        stations = self.directory.stations_by_region(state="Michigan", limit=10)

        self.assertGreater(len(stations), 0)
        self.assertTrue(all(station.station_id for station in stations))
        self.assertTrue(all(station.stream_url for station in stations))
        self.assertTrue(any(station.country_code == "US" for station in stations))

    def test_search_returns_named_station_results(self) -> None:
        stations = self.directory.search("WDET", limit=10)

        self.assertGreater(len(stations), 0)
        self.assertTrue(any("WDET" in station.name.upper() for station in stations))


if __name__ == "__main__":
    unittest.main()
