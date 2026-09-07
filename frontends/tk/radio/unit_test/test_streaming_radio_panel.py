# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest

from controllers.radio.streaming_radio_types import StreamingRadioStation
from frontends.tk.radio.streaming_radio_panel import is_explicit_internet_only


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

    def test_does_not_guess_from_station_name(self) -> None:
        station = StreamingRadioStation(
            station_id="wdet",
            name="WDET Detroit",
            stream_url="https://example.test/wdet",
            tags=("news", "jazz"),
        )

        self.assertFalse(is_explicit_internet_only(station))


if __name__ == "__main__":
    unittest.main()
