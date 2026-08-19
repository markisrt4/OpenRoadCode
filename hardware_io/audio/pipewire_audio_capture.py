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
    """

    def __init__(self, sample_rate_hz: int = 48000, frame_size: int = 2048) -> None:
        self._sample_rate_hz = sample_rate_hz
        self._frame_size = frame_size
        self._process: subprocess.Popen[bytes] | None = None

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
                "--device=@DEFAULT_MONITOR@",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def read(self) -> AudioFrame:
        if self._process is None or self._process.stdout is None:
            raise RuntimeError("audio capture has not been started")

        byte_count = self._frame_size * 4
        data = self._process.stdout.read(byte_count)
        if len(data) != byte_count:
            raise RuntimeError("audio capture ended unexpectedly")
        samples = np.frombuffer(data, dtype="<f4").astype(np.float64)
        return AudioFrame(tuple(float(value) for value in samples), self._sample_rate_hz)

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
