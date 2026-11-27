"""Trending detail lookups use the existing station and period filters."""

from unittest.mock import Mock, call

from apps.orcUi.adapters.musicforge_api_adapter import MusicForgeApiAdapter
from ui.radio.airplay_details import AirplayRequest


def test_song_station_breakdown_matches_both_title_and_artist(monkeypatch):
    adapter = MusicForgeApiAdapter("http://example.test")
    monkeypatch.setattr(
        adapter, "stations", Mock(return_value=[{"station": "WOMC"}, {"station": "WCSX"}])
    )
    charts = Mock(
        side_effect=[
            {"results": [{"artist": "Other", "title": "Song", "plays": 8}]},
            {"results": [{"artist": "Artist", "title": "Song", "plays": 3}]},
        ]
    )
    monkeypatch.setattr(adapter, "songs", charts)
    try:
        result = adapter.airplay_details(
            AirplayRequest("Artist", "Song", "7d", None, "stations"),
            current=lambda: True,
        )
    finally:
        adapter.close()

    assert result.counts == (("WOMC", 3), ("WCSX", None))
    assert not result.incomplete
    assert charts.call_args_list == [
        call(station="WCSX", period="7d", limit=40),
        call(station="WOMC", period="7d", limit=40),
    ]


def test_artist_period_comparison_keeps_station_filter(monkeypatch):
    adapter = MusicForgeApiAdapter("http://example.test")
    charts = Mock(side_effect=[{"results": []}, {}, {"results": [{"artist": "A", "plays": 9}]}])
    monkeypatch.setattr(adapter, "artists", charts)
    try:
        result = adapter.airplay_details(
            AirplayRequest("A", None, "7d", "WOMC", "trend"),
            current=lambda: True,
        )
    finally:
        adapter.close()

    assert result.counts == (("today", None), ("7d", None), ("30d", 9))
    assert charts.call_args_list == [
        call(station="WOMC", period=period, limit=40) for period in ("today", "7d", "30d")
    ]
