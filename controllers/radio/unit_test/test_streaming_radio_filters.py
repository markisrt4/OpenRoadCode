# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest

from controllers.radio.streaming_radio_filters import (
    StationFilters, is_explicit_internet_only, station_band,
    station_genre_matches, station_quality,
)
from controllers.radio.streaming_radio_types import StreamingRadioStation


def station(name: str, *, tags=(), bitrate=None) -> StreamingRadioStation:
    return StreamingRadioStation(
        station_id=name, name=name, stream_url="https://example.org/stream",
        tags=tags, bitrate_kbps=bitrate,
    )


class StationFiltersTest(unittest.TestCase):
    def test_all_includes_explicit_internet_and_unknown(self):
        stations = (station("FM", tags=("fm",)), station("Web", tags=("internet",)), station("Mystery"))
        self.assertEqual(StationFilters().apply(stations), stations)
        self.assertEqual(StationFilters(band="Internet-only").apply(stations), stations[1:2])
        self.assertEqual(StationFilters(band="Unknown").apply(stations), stations[2:])

    def test_genre_quality_and_band_combine_without_reordering(self):
        stations = (
            station("First", tags=("classic-rock", "fm"), bitrate=192),
            station("Second", tags=("rock", "fm"), bitrate=96),
            station("Third", tags=("rock", "internet"), bitrate=320),
            station("Fourth", tags=("jazz", "fm"), bitrate=320),
        )
        filters = StationFilters(genre="Rock", quality="High", band="FM")
        self.assertEqual(filters.active_count, 3)
        self.assertEqual(filters.apply(stations), stations[:1])
        self.assertEqual(StationFilters(band="Internet-only").apply(stations), stations[2:3])

    def test_quality_boundaries_and_unknown(self):
        self.assertEqual([station_quality(station(str(n), bitrate=n)) for n in (0, 95, 96, 191, 192)], ["Unknown", "Low", "Mid", "Mid", "High"])
        self.assertEqual(station_quality(station("missing")), "Unknown")

    def test_band_metadata_and_frequency_fallback(self):
        self.assertEqual(station_band(station("101.1", tags=("fm",))), "FM")
        self.assertEqual(station_band(station("101.1 FM")), "FM")
        self.assertEqual(station_band(station("760 AM")), "AM")
        self.assertEqual(station_band(station("Digital", tags=("dab+",))), "DAB")
        self.assertEqual(station_band(station("Mystery")), "Unknown")
        self.assertTrue(is_explicit_internet_only(station("Web", tags=("web-radio",))))

    def test_genre_aliases_and_invalid_selections(self):
        self.assertTrue(station_genre_matches(station("Rock", tags=("classic-rock",)), "Rock"))
        self.assertFalse(station_genre_matches(station("Rock", tags=("rock",)), "Jazz"))
        for kwargs in ({"genre": "Nope"}, {"quality": "Ultra"}, {"band": "Satellite"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                StationFilters(**kwargs)

    def test_filter_state_is_immutable_and_count_is_derived(self):
        filters = StationFilters(genre="Jazz", band="Internet-only")
        self.assertEqual(filters.active_count, 2)
        self.assertTrue(filters.internet_only)
        self.assertEqual(StationFilters().active_count, 0)
        with self.assertRaises(AttributeError):
            filters.genre = "Rock"


if __name__ == "__main__":
    unittest.main()
