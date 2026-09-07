# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest

from controllers.radio.adapters.radio_browser_directory import _parse_station
from controllers.radio.streaming_radio_types import StreamingRadioStation


class StreamingRadioStationTest(unittest.TestCase):
    def test_normalizes_optional_metadata(self) -> None:
        station = StreamingRadioStation(
            station_id=" abc ",
            name=" WDET ",
            stream_url=" https://example.test/live ",
            country_code="us",
            codec="aac",
            tags=(" news ", "", "jazz"),
        )

        self.assertEqual(station.station_id, "abc")
        self.assertEqual(station.name, "WDET")
        self.assertEqual(station.country_code, "US")
        self.assertEqual(station.codec, "AAC")
        self.assertEqual(station.tags, ("news", "jazz"))

    def test_rejects_missing_stream_url(self) -> None:
        with self.assertRaises(ValueError):
            StreamingRadioStation(station_id="abc", name="WDET", stream_url="")


class RadioBrowserPayloadTest(unittest.TestCase):
    def test_parses_resolved_stream_and_artwork(self) -> None:
        station = _parse_station(
            {
                "stationuuid": "station-1",
                "name": "Example FM",
                "url": "http://example.test/original",
                "url_resolved": "https://example.test/live.aac",
                "homepage": "https://example.test",
                "favicon": "https://example.test/logo.png",
                "state": "Michigan",
                "countrycode": "US",
                "codec": "AAC",
                "bitrate": 128,
                "tags": "local,news,talk",
            }
        )

        self.assertIsNotNone(station)
        assert station is not None
        self.assertEqual(station.stream_url, "https://example.test/live.aac")
        self.assertEqual(station.artwork_url, "https://example.test/logo.png")
        self.assertEqual(station.bitrate_kbps, 128)
        self.assertEqual(station.tags, ("local", "news", "talk"))

    def test_ignores_incomplete_station(self) -> None:
        self.assertIsNone(_parse_station({"stationuuid": "station-1", "name": "No Stream"}))


if __name__ == "__main__":
    unittest.main()
