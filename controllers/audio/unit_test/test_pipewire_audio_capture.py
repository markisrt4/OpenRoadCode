# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import io

import numpy as np

from controllers.audio.capture.pipewire_audio_capture import PipewireAudioCapture


def test_pipewire_capture_uses_raw_float32_stdout():
    capture = PipewireAudioCapture(sample_rate_hz=48_000, block_size=2048)

    assert capture._build_command() == [
        "pw-record",
        "--raw",
        "--format",
        "f32",
        "--rate",
        "48000",
        "--channels",
        "1",
        "-",
    ]


def test_pipewire_capture_includes_explicit_target():
    capture = PipewireAudioCapture(target="alsa_output.test")

    command = capture._build_command()

    assert command[-3:] == ["--target", "alsa_output.test", "-"]


class _ShortReadStream:
    def __init__(self, payload: bytes, chunk_sizes: tuple[int, ...]) -> None:
        self._payload = payload
        self._chunk_sizes = iter(chunk_sizes)
        self._offset = 0

    def read(self, size: int) -> bytes:
        if self._offset >= len(self._payload):
            return b""
        try:
            chunk_size = next(self._chunk_sizes)
        except StopIteration:
            chunk_size = size
        count = min(size, chunk_size, len(self._payload) - self._offset)
        chunk = self._payload[self._offset : self._offset + count]
        self._offset += count
        return chunk


class _Process:
    def __init__(self, stdout) -> None:
        self.stdout = stdout


def test_pipewire_capture_accumulates_short_reads_into_complete_blocks():
    samples = np.array([0.1, -0.2, 0.3, -0.4], dtype=np.float32)
    capture = PipewireAudioCapture(sample_rate_hz=48_000, block_size=4)
    capture._process = _Process(_ShortReadStream(samples.tobytes(), (3, 2, 1, 5, 5)))
    capture._running = True
    received: list[tuple[np.ndarray, int]] = []

    capture._read_loop(lambda block, rate: received.append((block, rate)))

    assert len(received) == 1
    block, rate = received[0]
    np.testing.assert_allclose(block, samples)
    assert rate == 48_000
    assert capture.is_running is False
