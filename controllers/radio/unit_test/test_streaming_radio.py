# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest
from unittest.mock import patch

from controllers.radio.adapters.radio_browser_directory import (
    RadioBrowserDirectory,
    _distance_km,
    _parse_station,
)
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
    def test_parses_resolved_stream_artwork_and_location(self) -> None:
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
                "geo_lat": 42.3314,
                "geo_long": -83.0458,
            }
        )

        self.assertIsNotNone(station)
        assert station is not None
        self.assertEqual(station.stream_url, "https://example.test/live.aac")
        self.assertEqual(station.artwork_url, "https://example.test/logo.png")
        self.assertEqual(station.bitrate_kbps, 128)
        self.assertEqual(station.tags, ("local", "news", "talk"))
        self.assertEqual(station.latitude, 42.3314)
        self.assertEqual(station.longitude, -83.0458)

    def test_ignores_incomplete_station(self) -> None:
        self.assertIsNone(_parse_station({"stationuuid": "station-1", "name": "No Stream"}))


class RadioBrowserIdentifierResolutionTest(unittest.TestCase):
    def test_resolves_ids_in_favorite_order_and_skips_duplicates(self) -> None:
        directory = RadioBrowserDirectory(api_base="https://radio.test/json")
        one = StreamingRadioStation(
            station_id="one",
            name="One",
            stream_url="https://example.test/one",
        )
        two = StreamingRadioStation(
            station_id="two",
            name="Two",
            stream_url="https://example.test/two",
        )

        with patch.object(
            directory,
            "_request_stations",
            return_value=(one, two),
        ) as mocked:
            stations = directory.stations_by_ids(("two", "one", "two", ""))

        self.assertEqual(
            tuple(station.station_id for station in stations),
            ("two", "one"),
        )
        mocked.assert_called_once()
        requested_url = mocked.call_args.args[0]
        self.assertIn("/stations/byuuid?", requested_url)
        self.assertIn("uuids=two%2Cone", requested_url)


class NearbyStationDiscoveryTest(unittest.TestCase):
    def test_distance_is_zero_for_same_position(self) -> None:
        self.assertAlmostEqual(_distance_km(42.3314, -83.0458, 42.3314, -83.0458), 0.0)

    def test_nearby_stations_are_sorted_then_missing_location_falls_back(self) -> None:
        directory = RadioBrowserDirectory()
        close = StreamingRadioStation(
            station_id="close",
            name="Close",
            stream_url="https://example.test/close",
            latitude=42.34,
            longitude=-83.05,
        )
        farther = StreamingRadioStation(
            station_id="farther",
            name="Farther",
            stream_url="https://example.test/farther",
            latitude=42.55,
            longitude=-83.20,
        )
        outside = StreamingRadioStation(
            station_id="outside",
            name="Outside",
            stream_url="https://example.test/outside",
            latitude=44.31,
            longitude=-85.60,
        )
        unknown = StreamingRadioStation(
            station_id="unknown",
            name="Unknown location",
            stream_url="https://example.test/unknown",
        )

        with patch.object(
            directory,
            "stations_by_region",
            return_value=(farther, outside, unknown, close),
        ):
            stations = directory.stations_near(
                latitude=42.3314,
                longitude=-83.0458,
                radius_km=80.0,
                state="Michigan",
                limit=10,
            )

        self.assertEqual(
            tuple(station.station_id for station in stations),
            ("close", "farther", "unknown"),
        )


if __name__ == "__main__":
    unittest.main()
