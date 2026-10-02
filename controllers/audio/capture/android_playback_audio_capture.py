# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Consume the consent-gated Android bridge playback stream.

The bridge owns MediaProjection and Android permissions. This adapter only
receives PCM and implements AudioCaptureIf. It cannot start native capture or
request consent, and it never stores the audio or exposes it to remote clients.
"""
from __future__ import annotations

import ipaddress
import struct
import threading
from urllib.parse import urlsplit
from urllib.request import urlopen

import numpy as np

from .audio_capture_if import AudioCaptureIf, AudioSamplesCallback


class AndroidPlaybackAudioCapture(AudioCaptureIf):
    """Read ORCA v1 mono PCM16 from the local Android playback bridge."""

    def __init__(self, *, url: str = "http://127.0.0.1:8768/stream",
                 block_size: int = 2048) -> None:
        parsed = urlsplit(url)
        if parsed.scheme != "http" or parsed.username or parsed.password or not parsed.hostname:
            raise ValueError("Android playback requires a local HTTP endpoint")
        try:
            local = ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError:
            local = False
        if not local:
            raise ValueError("Android playback is restricted to loopback")
        if block_size <= 0:
            raise ValueError("block_size must be positive")
        self.url = url
        self.block_size = block_size
        self._lock = threading.RLock()
        self._running = False
        self._response = None
        self._thread: threading.Thread | None = None
        self._generation = 0
        self.last_error: str | None = None

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def start(self, callback: AudioSamplesCallback) -> None:
        """Attach to an already-consented bridge and validate its PCM format."""
        with self._lock:
            if self._running:
                raise RuntimeError("Android playback capture is already running")
        response = urlopen(self.url, timeout=3)
        try:
            header = self._read_exact(response, 12)
            if len(header) != 12:
                raise RuntimeError("Android playback stream has an incomplete header")
            magic, rate, channels = struct.unpack("<4sII", header)
            if magic != b"ORCA" or not 8000 <= rate <= 192000 or channels != 1:
                raise RuntimeError("Unsupported Android playback PCM format")
        except Exception:
            response.close()
            raise
        with self._lock:
            self._generation += 1
            generation = self._generation
            self._response = response
            self._running = True
            self.last_error = None
            self._thread = threading.Thread(
                target=self._read_loop, args=(response, callback, rate, generation),
                name="orc-android-playback", daemon=True)
            self._thread.start()

    @staticmethod
    def _read_exact(stream, count: int) -> bytes:
        pending = bytearray()
        while len(pending) < count:
            chunk = stream.read(count - len(pending))
            if not chunk:
                break
            pending.extend(chunk)
        return bytes(pending)

    def _read_loop(self, response, callback: AudioSamplesCallback,
                   rate: int, generation: int) -> None:
        pending = bytearray()
        byte_count = self.block_size * 2
        try:
            while True:
                with self._lock:
                    if not self._running or generation != self._generation:
                        break
                chunk = response.read(byte_count - len(pending))
                if not chunk:
                    break
                pending.extend(chunk)
                if len(pending) < byte_count:
                    continue
                samples = np.frombuffer(pending, dtype="<i2").astype(np.float32) / 32768.0
                pending.clear()
                callback(samples, rate)
        except Exception as exc:
            with self._lock:
                if self._running and generation == self._generation:
                    self.last_error = str(exc)
        finally:
            with self._lock:
                if generation == self._generation:
                    self._running = False
                    self._response = None
            response.close()

    def stop(self) -> None:
        """Disconnect this consumer without stopping the Android projection."""
        with self._lock:
            self._running = False
            self._generation += 1
            response, thread = self._response, self._thread
            self._response = None
            self._thread = None
        if response is not None:
            response.close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1)
