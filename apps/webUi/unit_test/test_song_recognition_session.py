# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for the WebUI song-recognition adapter."""

from controllers.song_recognition import SongRecognitionIf, SongRecognitionResult
from apps.webUi.song_recognition_session import WebSongRecognitionSession


class _Recognizer(SongRecognitionIf):
    @property
    def is_configured(self) -> bool:
        return True

    @property
    def provider_name(self) -> str | None:
        return "test"

    def recognize(self, audio: bytes, *, sample_bytes: int | None = None) -> SongRecognitionResult | None:
        assert audio == b"clip"
        assert sample_bytes == 4
        return SongRecognitionResult(
            title="Test Song",
            artists=("Test Artist",),
            album="Test Album",
            provider="test",
        )


def test_unconfigured_session_reports_provider_state(monkeypatch) -> None:
    monkeypatch.delenv("ACRCLOUD_HOST", raising=False)
    monkeypatch.delenv("ACRCLOUD_ACCESS_KEY", raising=False)
    monkeypatch.delenv("ACRCLOUD_ACCESS_SECRET", raising=False)
    session = WebSongRecognitionSession()
    assert session.config() == {"configured": False, "provider": None}
    assert session.recognize(b"clip")["matched"] is False


def test_recognition_result_is_normalized_for_json() -> None:
    session = WebSongRecognitionSession(_Recognizer())
    result = session.recognize(b"clip")
    assert result["matched"] is True
    assert result["configured"] is True
    assert result["provider"] == "test"
    assert result["song"]["title"] == "Test Song"
    assert result["song"]["artists"] == ["Test Artist"]
