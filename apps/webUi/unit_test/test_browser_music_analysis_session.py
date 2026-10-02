# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for browser PCM music-analysis transport."""
from __future__ import annotations

import math
import struct

import pytest

from apps.webUi.browser_music_analysis_session import WebBrowserMusicAnalysisSession
from controllers.audio.music_analysis import MusicAnalysisState, MusicAnalyzer


def _pcm16_sine(*, frequency_hz: float, sample_rate_hz: int, sample_count: int) -> bytes:
    values = []
    for index in range(sample_count):
        sample = 0.5 * math.sin(2.0 * math.pi * frequency_hz * index / sample_rate_hz)
        values.append(round(sample * 32767.0))
    return struct.pack(f"<{sample_count}h", *values)


def test_idle_state_matches_analyzer_configuration() -> None:
    session = WebBrowserMusicAnalysisSession(MusicAnalyzer(fft_size=1024, band_count=12))

    state = session.state()

    assert state["level"] == 0.0
    assert state["sample_rate_hz"] == 0
    assert state["fft_size"] == 1024
    assert state["spectrum"] == [0.0] * 12
    assert state["zeroized"] is False


@pytest.mark.parametrize(
    ("audio", "sample_rate_hz", "message"),
    [
        (b"", 48000, "Empty PCM frame"),
        (b"\x00", 48000, "complete 16-bit samples"),
        (b"\x00\x00", 0, "sample_rate_hz must be positive"),
    ],
)
def test_invalid_pcm_frames_are_rejected(audio: bytes, sample_rate_hz: int, message: str) -> None:
    session = WebBrowserMusicAnalysisSession()

    with pytest.raises(ValueError, match=message):
        session.push_pcm16(audio, sample_rate_hz)


def test_pcm16_frame_is_analyzed_and_retained() -> None:
    sample_rate_hz = 48000
    fft_size = 2048
    session = WebBrowserMusicAnalysisSession(MusicAnalyzer(fft_size=fft_size))
    audio = _pcm16_sine(
        frequency_hz=60.0,
        sample_rate_hz=sample_rate_hz,
        sample_count=fft_size,
    )

    state = session.push_pcm16(audio, sample_rate_hz)

    assert state["sample_rate_hz"] == sample_rate_hz
    assert state["fft_size"] == fft_size
    assert state["level"] > 0.0
    assert state["bass"] > state["mid"]
    assert state["bass"] > state["treble"]
    assert session.state() == state


def test_analyzed_frame_is_published_to_consumer() -> None:
    sample_rate_hz = 48000
    fft_size = 1024
    received: list[MusicAnalysisState] = []
    session = WebBrowserMusicAnalysisSession(
        MusicAnalyzer(fft_size=fft_size),
        consumer=received.append,
    )
    audio = _pcm16_sine(
        frequency_hz=1000.0,
        sample_rate_hz=sample_rate_hz,
        sample_count=fft_size,
    )

    returned = session.push_pcm16(audio, sample_rate_hz)

    assert len(received) == 1
    assert received[0].sample_rate_hz == sample_rate_hz
    assert received[0].fft_size == fft_size
    assert returned["mid"] == received[0].mid


def test_zeroize_lifecycle_is_forwarded_to_analyzer() -> None:
    sample_rate_hz = 48000
    fft_size = 1024
    session = WebBrowserMusicAnalysisSession(MusicAnalyzer(fft_size=fft_size))
    silence = b"\x00\x00" * fft_size

    session.start_zeroize()
    session.push_pcm16(silence, sample_rate_hz)
    state = session.finish_zeroize()

    assert state["zeroized"] is True
    assert session.clear_zeroize()["zeroized"] is False
