# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility adapters for the original browser and Linux HTTP routes."""
from __future__ import annotations

from controllers.audio.music_analysis.music_analysis_session import MusicAnalysisSession


class WebMusicAnalysisSourceSession:
    """Expose one named source without creating another analyzer.

    New callers should use MusicAnalysisSession directly. This adapter keeps
    existing source-specific HTTP routes working during the migration.
    """

    def __init__(self, session: MusicAnalysisSession, source: str) -> None:
        self._session = session
        self._source = source

    def state(self) -> dict[str, object]:
        return self._session.state()

    def start(self) -> dict[str, object]:
        return self._session.start(self._source)

    def stop(self) -> dict[str, object]:
        if self._session.state()["source"] == self._source:
            return self._session.stop()
        return self._session.state()

    def push_pcm16(self, audio: bytes, sample_rate_hz: int) -> dict[str, object]:
        current = self._session.state()
        if current["source"] is None:
            self._session.start(self._source)
        return self._session.push_pcm16(audio, sample_rate_hz, source=self._source)

    def start_zeroize(self) -> dict[str, object]:
        self._require_selected()
        return self._session.start_zeroize()

    def finish_zeroize(self) -> dict[str, object]:
        self._require_selected()
        return self._session.finish_zeroize()

    def clear_zeroize(self) -> dict[str, object]:
        self._require_selected()
        return self._session.clear_zeroize()

    def _require_selected(self) -> None:
        if self._session.state()["source"] != self._source:
            raise RuntimeError(f"Select {self._source} before calibration")
