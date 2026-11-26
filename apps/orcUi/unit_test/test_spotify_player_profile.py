"""Check the Spotify player's dedicated Chromium profile configuration."""

import json

from apps.orcUi.adapters.spotify_local_player_factory import _make_browser


def test_player_enables_protected_audio_in_its_dedicated_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    profile = tmp_path / "openroadcode" / "spotify-player-browser"
    preferences = profile / "Default" / "Preferences"
    preferences.parent.mkdir(parents=True)
    preferences.write_text(
        '{"webkit":{"webprefs":{"encrypted_media_enabled":false,"other":3}},"other":1}',
        encoding="utf-8",
    )

    browser = _make_browser("http://127.0.0.1:8771/")

    assert browser.profile_path == profile
    assert json.loads(preferences.read_text(encoding="utf-8")) == {
        "webkit": {"webprefs": {"encrypted_media_enabled": True, "other": 3}},
        "other": 1,
    }


def test_player_configures_a_new_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    browser = _make_browser("http://127.0.0.1:8771/")

    assert browser.profile_path is not None
    preferences = browser.profile_path / "Default" / "Preferences"
    assert json.loads(preferences.read_text(encoding="utf-8")) == {
        "webkit": {"webprefs": {"encrypted_media_enabled": True}}
    }
