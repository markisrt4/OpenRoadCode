# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import shutil
import subprocess

import numpy as np

from .audio_capture_if import AudioCaptureIf, AudioFrame


class PipeWireAudioCapture(AudioCaptureIf):
    """Capture the default PipeWire/PulseAudio monitor as mono float PCM.

    PipeWire's PulseAudio compatibility layer exposes sink monitor sources.
    ``parec`` gives us a deliberately small first implementation without
    coupling the analyzer to a Python audio library.

    Frames may overlap so analysis can update more frequently without reducing
    the FFT window size (and therefore frequency resolution).
    """

    def __init__(
        self,
        sample_rate_hz: int = 48000,
        frame_size: int = 2048,
        hop_size: int = 1024,
        latency_msec: int = 10,
        device: str = "@DEFAULT_MONITOR@",
    ) -> None:
        if hop_size <= 0 or hop_size > frame_size:
            raise ValueError("hop_size must be in the range 1..frame_size")

        self._sample_rate_hz = sample_rate_hz
        self._frame_size = frame_size
        self._hop_size = hop_size
        self._latency_msec = latency_msec
        self._device = device.strip() or "@DEFAULT_MONITOR@"
        self._process: subprocess.Popen[bytes] | None = None
        self._frame_buffer: np.ndarray | None = None

    def start(self) -> None:
        if self._process is not None:
            return
        if shutil.which("parec") is None:
            raise RuntimeError("parec is required (Debian package: pulseaudio-utils)")

        self._process = subprocess.Popen(
            [
                "parec",
                "--format=float32le",
                "--channels=1",
                f"--rate={self._sample_rate_hz}",
                f"--latency-msec={self._latency_msec}",
                f"--device={self._device}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self._frame_buffer = None

    def _read_samples(self, sample_count: int) -> np.ndarray:
        if self._process is None or self._process.stdout is None:
            raise RuntimeError("audio capture has not been started")

        byte_count = sample_count * 4
        data = self._process.stdout.read(byte_count)
        if len(data) != byte_count:
            raise RuntimeError("audio capture ended unexpectedly")
        return np.frombuffer(data, dtype="<f4").astype(np.float64)

    def read(self) -> AudioFrame:
        if self._frame_buffer is None:
            # Prime the first complete FFT window.
            self._frame_buffer = self._read_samples(self._frame_size)
            new_sample_count = self._frame_size
        else:
            # Keep the newest samples from the previous window and append only
            # one hop of fresh audio. With the defaults this gives 50% overlap:
            # 2048-sample FFT windows updated every 1024 samples (~21.3 ms).
            new_samples = self._read_samples(self._hop_size)
            retained = self._frame_buffer[self._hop_size :]
            self._frame_buffer = np.concatenate((retained, new_samples))
            new_sample_count = self._hop_size

        return AudioFrame(
            tuple(float(value) for value in self._frame_buffer),
            self._sample_rate_hz,
            new_sample_count,
        )

    def stop(self) -> None:
        if self._process is None:
            return
        self._process.terminate()
        try:
            self._process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
        self._process = None
        self._frame_buffer = None
