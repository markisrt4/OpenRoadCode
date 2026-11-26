"""Tests for MusicForge URL selection on desktop and manual launches."""

import pytest

from common.musicforge_airplay import (
    DEFAULT_AIRPLAY_URL,
    musicforge_airplay_url,
    validate_airplay_url,
)


def test_endpoint_precedence(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("MUSICFORGE_AIRPLAY_URL", raising=False)
    config_dir = tmp_path / "openroadcode"
    config_dir.mkdir()
    endpoint = config_dir / "musicforge-airplay-url"

    assert musicforge_airplay_url() == DEFAULT_AIRPLAY_URL
    endpoint.write_text("invalid\n", encoding="utf-8")
    assert musicforge_airplay_url() == DEFAULT_AIRPLAY_URL
    endpoint.write_text("https://airplay.example.com/\n", encoding="utf-8")
    assert musicforge_airplay_url() == "https://airplay.example.com"
    monkeypatch.setenv("MUSICFORGE_AIRPLAY_URL", "http://127.0.0.1:8003")
    assert musicforge_airplay_url() == "http://127.0.0.1:8003"


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/airplay",
        "https://user:password@airplay.example.com",
        "http://localhost:99999",
        "http://localhost:0",
        "https://airplay.example.com?token=secret",
    ],
)
def test_reject_invalid_endpoints(url):
    with pytest.raises(ValueError):
        validate_airplay_url(url)
