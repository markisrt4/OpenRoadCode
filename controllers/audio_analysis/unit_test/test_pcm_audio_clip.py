# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import io
import wave
import numpy as np

from controllers.audio_analysis.pcm_music_analysis_source import PcmMusicAnalysisSource
from controllers.audio_analysis.pushed_pcm_music_analysis_source import PushedPcmMusicAnalysisSource
from hardware_io.audio.audio_capture_if import AudioCaptureIf, AudioFrame


class _OverlappingCapture(AudioCaptureIf):
    def __init__(self) -> None:
        self.frames = iter((
            AudioFrame((1., 2., 3., 4.), 4, 4),
            AudioFrame((3., 4., 5., 6.), 4, 2),
        ))

    def start(self) -> None: pass
    def read(self) -> AudioFrame: return next(self.frames)
    def stop(self) -> None: pass


def test_recent_audio_wav_wraps_pcm_with_format_metadata() -> None:
    source=PushedPcmMusicAnalysisSource()
    source.push_frame((0.0,.25,-.25,0.0),48_000)

    clip=source.recent_audio_wav()

    assert clip.startswith(b"RIFF") and clip[8:12]==b"WAVE"
    with wave.open(io.BytesIO(clip),"rb") as wav:
        assert wav.getnchannels()==1
        assert wav.getsampwidth()==2
        assert wav.getframerate()==48_000
        assert wav.getnframes()==4


def test_recent_audio_buffer_is_limited_by_time_not_chunk_count() -> None:
    source=PushedPcmMusicAnalysisSource();rate=100
    for _ in range(15):source.push_frame(tuple(.1 for _ in range(100)),rate)

    with wave.open(io.BytesIO(source.recent_audio_wav(10)),"rb") as wav:
        assert wav.getnframes()==1_000


def test_reports_buffered_audio_duration() -> None:
    source=PushedPcmMusicAnalysisSource();rate=100
    source.push_frame(tuple(.1 for _ in range(250)),rate)

    assert source.buffered_audio_seconds == 2.5


def test_pcm_source_buffers_only_fresh_samples_from_overlapping_windows() -> None:
    source=PcmMusicAnalysisSource(_OverlappingCapture())
    first=next(source._capture.frames);second=next(source._capture.frames)
    for frame in (first,second):source._buffer_audio_frame(frame)

    pcm=np.frombuffer(source.recent_audio_pcm16(10),dtype="<i2")
    assert source.buffered_audio_seconds == 1.5
    assert pcm.size == 6
