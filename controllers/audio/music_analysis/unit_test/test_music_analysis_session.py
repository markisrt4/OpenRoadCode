# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract tests for source-independent audio analysis ownership."""
import struct
from dataclasses import dataclass

import pytest

from controllers.audio.music_analysis.music_analysis_session import MusicAnalysisSession, PushAudioCapture


@dataclass(frozen=True)
class FakeState:
    level: float
    bass: float = 0.0
    mid: float = 0.0
    treble: float = 0.0
    spectrum: tuple[float, ...] = (0.0, 0.0, 0.0)
    percussion: object = None
    sample_rate_hz: int = 48000
    fft_size: int = 2048


class FakeAnalyzer:
    band_count = 3
    fft_size = 2048

    def __init__(self):
        self.frames = []
        self.is_zeroized = False
        self.collecting = False
        self.collected = 0
        self.clears = 0

    def analyze(self, samples, rate):
        self.frames.append((tuple(samples), rate))
        if self.collecting:
            self.collected += 1
        return FakeState(level=abs(float(samples[0])), sample_rate_hz=rate)

    def start_zeroize(self):
        self.collecting = True
        self.collected = 0

    def finish_zeroize(self):
        self.collecting = False
        if not self.collected:
            raise RuntimeError("zeroize requires at least one analyzed audio block")
        self.is_zeroized = True

    def clear_zeroize(self):
        self.collecting = False
        self.collected = 0
        self.is_zeroized = False
        self.clears += 1


class FakeCapture:
    def __init__(self, events, name, fail=False):
        self.events = events
        self.name = name
        self.fail = fail
        self.callback = None
        self.running = False

    @property
    def is_running(self):
        return self.running

    def start(self, callback):
        self.events.append((self.name, "start"))
        self.callback = callback
        if self.fail:
            raise RuntimeError("backend unavailable")
        self.running = True

    def stop(self):
        self.events.append((self.name, "stop"))
        self.running = False

    def emit(self, samples=(0.25,), rate=48000):
        self.callback(samples, rate)


def test_source_selection_is_lazy_idempotent_and_exclusive():
    events, captures = [], []
    def factory(name):
        def create():
            capture = FakeCapture(events, name)
            captures.append(capture)
            return capture
        return create
    analyzer = FakeAnalyzer()
    session = MusicAnalysisSession({"one": factory("one"), "two": factory("two")}, analyzer=analyzer)
    assert session.sources() == ("one", "two")
    assert not captures
    assert session.start("one")["running"]
    assert session.start("one")["running"]
    assert len(captures) == 1
    session.start("two")
    assert events == [("one", "start"), ("one", "stop"), ("two", "start")]
    assert not captures[0].running
    assert captures[1].running
    assert session.state()["source"] == "two"
    assert analyzer.clears == 2
    session.stop()
    assert not session.state()["running"]
    assert session.state()["source"] == "two"


def test_unknown_source_does_not_interrupt_current_capture():
    session = MusicAnalysisSession({"browser": PushAudioCapture}, analyzer=FakeAnalyzer())
    session.start("browser")
    with pytest.raises(ValueError, match="Unknown audio source"):
        session.start("missing")
    assert session.state()["running"]
    assert session.state()["source"] == "browser"


def test_push_pcm16_uses_same_analyzer_and_rejects_other_sources():
    analyzer = FakeAnalyzer()
    session = MusicAnalysisSession({"browser": PushAudioCapture, "other": PushAudioCapture}, analyzer=analyzer)
    session.start("browser")
    data = session.push_pcm16(struct.pack("<3h", -32768, 0, 32767), 48000)
    assert analyzer.frames[-1][0] == (-1.0, 0.0, 32767 / 32768.0)
    assert data["level"] == 1.0
    assert data["source"] == "browser"
    with pytest.raises(ValueError, match="complete 16-bit"):
        session.push_pcm16(b"x", 48000)
    with pytest.raises(ValueError, match="positive"):
        session.push_pcm16(b"\0\0", 0)
    with pytest.raises(RuntimeError, match="does not accept"):
        session.push((0.1,), 48000, source="other")
    session.stop()
    with pytest.raises(RuntimeError, match="not running"):
        session.push_pcm16(b"\0\0", 48000)


def test_calibration_is_shared_and_source_switch_resets_profile():
    analyzer = FakeAnalyzer()
    session = MusicAnalysisSession({"browser": PushAudioCapture, "other": PushAudioCapture}, analyzer=analyzer)
    with pytest.raises(RuntimeError, match="Start an audio source"):
        session.start_zeroize()
    session.start("browser")
    assert session.start_zeroize()["calibrating"]
    session.push((0.02,), 48000, source="browser")
    result = session.finish_zeroize()
    assert result["zeroized"]
    assert not result["calibrating"]
    assert session.start("browser")["zeroized"]
    result = session.start("other")
    assert not result["zeroized"]
    assert not result["calibrating"]
    assert result["level"] == 0.0
    assert analyzer.clears == 2


def test_stopping_during_calibration_discards_unfinished_collection():
    analyzer = FakeAnalyzer()
    session = MusicAnalysisSession({"browser": PushAudioCapture}, analyzer=analyzer)
    session.start("browser")
    session.start_zeroize()
    session.push((0.01,), 48000, source="browser")
    session.stop()
    assert not analyzer.collecting
    assert not session.state()["calibrating"]
    session.start()
    with pytest.raises(RuntimeError, match="at least one"):
        session.finish_zeroize()
    assert not session.state()["calibrating"]


def test_stale_capture_callback_cannot_update_new_source():
    events, captures, published = [], [], []
    def factory(name):
        def create():
            capture = FakeCapture(events, name)
            captures.append(capture)
            return capture
        return create
    analyzer = FakeAnalyzer()
    session = MusicAnalysisSession({"one": factory("one"), "two": factory("two")}, analyzer=analyzer, consumer=published.append)
    session.start("one")
    old = captures[0]
    old.emit()
    session.start("two")
    count = len(analyzer.frames)
    old.emit((0.9,))
    assert len(analyzer.frames) == count
    assert len(published) == count
    captures[1].emit((0.5,))
    assert session.state()["level"] == 0.5
    assert len(published) == count + 1


def test_failed_backend_start_can_be_retried_without_false_running_state():
    events = []
    capture = FakeCapture(events, "broken", fail=True)
    session = MusicAnalysisSession({"broken": lambda: capture}, analyzer=FakeAnalyzer())
    with pytest.raises(RuntimeError, match="backend unavailable"):
        session.start("broken")
    assert not session.state()["running"]
    assert session.state()["source"] == "broken"
    capture.fail = False
    assert session.start()["running"]
    session.stop()
    session.stop()
    assert not session.state()["running"]


def test_push_source_requires_running_capture_and_valid_pcm():
    capture = PushAudioCapture()
    with pytest.raises(RuntimeError, match="not running"):
        capture.push((0.1,), 48000)
    capture.start(lambda samples, rate: None)
    with pytest.raises(ValueError, match="complete 16-bit"):
        capture.push_pcm16(b"", 48000)
    with pytest.raises(ValueError, match="positive"):
        capture.push((0.1,), 0)
    capture.stop()
    assert not capture.is_running
