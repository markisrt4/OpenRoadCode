# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""PipeWire audio capture using pw-record's raw PCM output."""
from __future__ import annotations

import shutil
import subprocess
import threading

import numpy as np

from .audio_capture_if import AudioCaptureIf, AudioSamplesCallback


class PipewireAudioCapture(AudioCaptureIf):
    """Capture mono float32 PCM from PipeWire in a background thread."""

    def __init__(
        self,
        *,
        sample_rate_hz: int = 48_000,
        block_size: int = 2048,
        target: str | None = None,
    ) -> None:
        if sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive")
        if block_size <= 0:
            raise ValueError("block_size must be positive")
        self.sample_rate_hz = sample_rate_hz
        self.block_size = block_size
        self.target = target
        self._process: subprocess.Popen[bytes] | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, callback: AudioSamplesCallback) -> None:
        if self._running:
            raise RuntimeError("audio capture is already running")
        if shutil.which("pw-record") is None:
            raise RuntimeError("pw-record was not found; install PipeWire tools")

        self._process = subprocess.Popen(
            self._build_command(),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        self._running = True
        self._thread = threading.Thread(
            target=self._read_loop,
            args=(callback,),
            name="pipewire-audio-capture",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        process = self._process
        self._process = None
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1.0)
        thread = self._thread
        self._thread = None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)

    def _build_command(self) -> list[str]:
        """Build a pw-record command that emits headerless float32 PCM."""
        command = [
            "pw-record",
            "--raw",
            "--format",
            "f32",
            "--rate",
            str(self.sample_rate_hz),
            "--channels",
            "1",
        ]
        if self.target:
            command.extend(["--target", self.target])
        command.append("-")
        return command

    def _read_loop(self, callback: AudioSamplesCallback) -> None:
        process = self._process
        if process is None or process.stdout is None:
            self._running = False
            return
        byte_count = self.block_size * np.dtype(np.float32).itemsize
        try:
            while self._running:
                data = process.stdout.read(byte_count)
                if not data or len(data) < byte_count:
                    break
                samples = np.frombuffer(data, dtype=np.float32).copy()
                callback(samples, self.sample_rate_hz)
        finally:
            self._running = False
