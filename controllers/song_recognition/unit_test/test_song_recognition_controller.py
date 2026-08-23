# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import io
import math
import wave

import pytest

from controllers.song_recognition.song_recognition_controller import SongRecognitionController


def _wav(seconds: float, amplitude: float = .1) -> bytes:
    rate=8_000;frames=int(rate*seconds);pcm=bytearray()
    for index in range(frames):pcm.extend(int(amplitude*32767*math.sin(2*math.pi*440*index/rate)).to_bytes(2,"little",signed=True))
    output=io.BytesIO()
    with wave.open(output,"wb") as clip:clip.setnchannels(1);clip.setsampwidth(2);clip.setframerate(rate);clip.writeframes(bytes(pcm))
    return output.getvalue()


def test_describes_usable_recognition_clip() -> None:
    summary=SongRecognitionController._describe_wav(_wav(10))
    assert summary.startswith("10.0s clip · ")


def test_rejects_effectively_silent_clip() -> None:
    with pytest.raises(RuntimeError,match="effectively silent"):
        SongRecognitionController._describe_wav(_wav(10,0.0))


def test_rejects_clip_before_recognition_window_is_ready() -> None:
    with pytest.raises(RuntimeError, match="let the song play for at least 10 seconds"):
        SongRecognitionController._describe_wav(_wav(7))
