"""Tests for saving a verified Airplay endpoint."""

from io import BytesIO

import pytest

from common.musicforge_airplay import musicforge_airplay_url
from scripts.installers import setup_musicforge_airplay


def test_setup_preserves_existing_url_when_verification_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("MUSICFORGE_AIRPLAY_URL", raising=False)
    requests = []

    def stations(url, *, timeout):
        requests.append((url, timeout))
        return BytesIO(b'{"stations": []}' if len(requests) == 1 else b'{"error":"not found"}')

    monkeypatch.setattr(setup_musicforge_airplay, "urlopen", stations)
    setup_musicforge_airplay.configure_airplay("https://airplay.example.com/")
    with pytest.raises(ValueError, match="station list"):
        setup_musicforge_airplay.configure_airplay("https://wrong.example.com")

    assert requests == [
        ("https://airplay.example.com/api/v1/stations", 5),
        ("https://wrong.example.com/api/v1/stations", 5),
    ]
    assert musicforge_airplay_url() == "https://airplay.example.com"
