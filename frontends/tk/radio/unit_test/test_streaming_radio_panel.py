# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest

from controllers.radio.streaming_radio_types import StreamingRadioStation
from frontends.tk.radio.streaming_radio_panel import (
    is_explicit_internet_only,
    station_band,
    station_genre_matches,
    station_quality,
)


class StreamingRadioPanelClassificationTest(unittest.TestCase):
    def test_recognizes_explicit_internet_only_tags(self) -> None:
        for tag in ("internet", "internet-only", "online only", "web_radio", "webradio"):
            with self.subTest(tag=tag):
                station = StreamingRadioStation(
                    station_id=f"station-{tag}",
                    name="Internet Station",
                    stream_url="https://example.test/live",
                    tags=(tag,),
                )
                self.assertTrue(is_explicit_internet_only(station))

    def test_does_not_guess_internet_only_from_station_name(self) -> None:
        station = StreamingRadioStation(
            station_id="wdet",
            name="WDET Detroit",
            stream_url="https://example.test/wdet",
            tags=("news", "jazz"),
        )
        self.assertFalse(is_explicit_internet_only(station))

    def test_normalizes_genre_tags_into_orc_categories(self) -> None:
        station = StreamingRadioStation(
            station_id="wmuz",
            name="103.5 The Light",
            stream_url="https://example.test/wmuz",
            tags=("Christian Contemporary", "talk"),
        )
        self.assertTrue(station_genre_matches(station, "Christian"))
        self.assertTrue(station_genre_matches(station, "News/Talk"))
        self.assertFalse(station_genre_matches(station, "Jazz"))

    def test_quality_buckets_use_stream_bitrate(self) -> None:
        cases = ((64, "Low"), (95, "Low"), (96, "Mid"), (191, "Mid"), (192, "High"), (320, "High"), (None, "Unknown"))
        for bitrate, expected in cases:
            with self.subTest(bitrate=bitrate):
                station = StreamingRadioStation(
                    station_id=f"station-{bitrate}",
                    name="Test",
                    stream_url="https://example.test/live",
                    bitrate_kbps=bitrate,
                )
                self.assertEqual(station_quality(station), expected)

    def test_infers_fm_from_frequency_in_station_name(self) -> None:
        station = StreamingRadioStation(
            station_id="wmuz",
            name="103.5 The Light",
            stream_url="https://example.test/wmuz",
            tags=("christian",),
        )
        self.assertEqual(station_band(station), "FM")

    def test_prefers_explicit_band_tags(self) -> None:
        fm = StreamingRadioStation(
            station_id="fm",
            name="Station One",
            stream_url="https://example.test/fm",
            tags=("fm",),
        )
        am = StreamingRadioStation(
            station_id="am",
            name="Station Two",
            stream_url="https://example.test/am",
            tags=("medium_wave",),
        )
        dab = StreamingRadioStation(
            station_id="dab",
            name="Station Three",
            stream_url="https://example.test/dab",
            tags=("DAB+",),
        )
        self.assertEqual(station_band(fm), "FM")
        self.assertEqual(station_band(am), "AM")
        self.assertEqual(station_band(dab), "DAB")


if __name__ == "__main__":
    unittest.main()
