# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""RTL-SDR implementation of the hardware-independent SDR source contract."""

from __future__ import annotations

import ctypes
import ctypes.util
import queue
import threading
import time
from typing import Any

from hardware_io.sdr.sdr_source_if import SdrSourceIf
from hardware_io.sdr.sdr_types import IqBlock, SdrCapabilities


class RtlSdrSource(SdrSourceIf):
    """Acquire unsigned 8-bit interleaved IQ through librtlsdr."""

    DEFAULT_SAMPLE_RATE_HZ = 2_400_000
    DEFAULT_BLOCK_BYTES = 262_144
    MIN_FREQUENCY_HZ = 24_000_000
    MAX_FREQUENCY_HZ = 1_766_000_000

    def __init__(
        self,
        device_index: int = 0,
        block_bytes: int = DEFAULT_BLOCK_BYTES,
        library: Any | None = None,
        acquisition_mode: str = "auto",
        queue_blocks: int = 32,
    ) -> None:
        if device_index < 0:
            raise ValueError("device_index must be non-negative")
        if block_bytes <= 0 or block_bytes % 512:
            raise ValueError("block_bytes must be a positive multiple of 512")
        if block_bytes % 2:
            raise ValueError("block_bytes must contain complete IQ pairs")

        if acquisition_mode not in ("auto", "sync", "async"):
            raise ValueError("acquisition_mode must be auto, sync, or async")
        if queue_blocks <= 0:
            raise ValueError("queue_blocks must be positive")
        self._acquisition_mode = acquisition_mode
        self._queue = queue.Queue(maxsize=queue_blocks)
        self._worker: threading.Thread | None = None
        self._callback = None
        self._worker_error: str | None = None
        self._dropped_blocks = 0
        self._received_blocks = 0
        self._device_index = device_index
        self._block_bytes = block_bytes
        self._library = library
        self._device = ctypes.c_void_p()
        self._center_frequency_hz = 0
        self._sample_rate_hz = self.DEFAULT_SAMPLE_RATE_HZ
        self._gain_db: float | None = None
        self._rtl_agc_enabled = False
        self._running = False

    def open(self) -> None:
        """Load librtlsdr and open the selected RTL-SDR device."""
        if self.is_connected():
            return

        library = self._library or self._load_library()
        self._configure_library(library)

        device = ctypes.c_void_p()
        self._check(library.rtlsdr_open(ctypes.byref(device), self._device_index), "open device")
        if not device.value:
            raise RuntimeError("librtlsdr opened the device without returning a handle")

        self._library = library
        self._device = device
        try:
            self.set_sample_rate(self._sample_rate_hz)
            self.set_gain(self._gain_db)
            self.set_rtl_agc(self._rtl_agc_enabled)
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        """Stop acquisition and close the librtlsdr device."""
        if not self.is_connected():
            self._running = False
            return
        self.stop()
        assert self._library is not None
        device = self._device
        self._device = ctypes.c_void_p()
        self._check(self._library.rtlsdr_close(device), "close device")

    def is_connected(self) -> bool:
        return bool(self._device.value)

    def get_capabilities(self) -> SdrCapabilities:
        return SdrCapabilities(
            min_frequency_hz=self.MIN_FREQUENCY_HZ,
            max_frequency_hz=self.MAX_FREQUENCY_HZ,
            min_sample_rate_hz=225_001,
            max_sample_rate_hz=3_200_000,
            supports_manual_gain=True,
        )

    def set_center_frequency(self, frequency_hz: int) -> None:
        device, library = self._require_device()
        if not self.MIN_FREQUENCY_HZ <= frequency_hz <= self.MAX_FREQUENCY_HZ:
            raise ValueError(f"center frequency outside RTL-SDR range: {frequency_hz}")
        self._check(library.rtlsdr_set_center_freq(device, frequency_hz), "set center frequency")
        self._center_frequency_hz = frequency_hz

    def get_center_frequency(self) -> int:
        return self._center_frequency_hz

    def set_sample_rate(self, sample_rate_hz: int) -> None:
        device, library = self._require_device()
        if sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive")
        self._check(library.rtlsdr_set_sample_rate(device, sample_rate_hz), "set sample rate")
        self._sample_rate_hz = sample_rate_hz

    def get_sample_rate(self) -> int:
        return self._sample_rate_hz

    def set_gain(self, gain_db: float | None) -> None:
        device, library = self._require_device()
        if gain_db is None:
            self._check(library.rtlsdr_set_tuner_gain_mode(device, 0), "enable automatic gain")
            self._gain_db = None
            return

        self._check(library.rtlsdr_set_tuner_gain_mode(device, 1), "enable manual gain")
        gain_tenths_db = round(gain_db * 10.0)
        self._check(library.rtlsdr_set_tuner_gain(device, gain_tenths_db), "set tuner gain")
        self._gain_db = gain_db

    def set_rtl_agc(self, enabled: bool) -> None:
        """Configure RTL2832 digital AGC independently of tuner gain."""
        device, library = self._require_device()
        setter = getattr(library, "rtlsdr_set_agc_mode", None)
        if setter is None:
            if enabled:
                raise RuntimeError("librtlsdr does not expose rtlsdr_set_agc_mode")
            return
        self._check(setter(device, int(enabled)), "set RTL digital AGC")
        self._rtl_agc_enabled = enabled

    def start(self) -> None:
        device, library = self._require_device()
        if self._running:
            return
        self._check(library.rtlsdr_reset_buffer(device), "reset IQ buffer")
        self._queue = queue.Queue(maxsize=self._queue.maxsize)
        self._worker_error = None
        self._dropped_blocks = 0
        self._received_blocks = 0
        self._running = True
        if self._use_async(library):
            self._callback = ctypes.CFUNCTYPE(None, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_uint32, ctypes.c_void_p)(self._on_iq)
            self._worker = threading.Thread(target=self._run_async, name="rtl-sdr-async", daemon=True)
            self._worker.start()

    def stop(self) -> None:
        self._running = False
        worker = self._worker
        if worker is not None:
            if self.is_connected():
                self._check(self._library.rtlsdr_cancel_async(self._device), "cancel async IQ")
            worker.join(timeout=5.0)
            if worker.is_alive():
                raise RuntimeError("RTL-SDR async worker did not stop; refusing to close device")
            self._worker = None
            self._callback = None

    def get_acquisition_stats(self) -> dict[str, int]:
        return {"received_blocks": self._received_blocks,
                "dropped_blocks": self._dropped_blocks,
                "queued_blocks": self._queue.qsize()}

    def _use_async(self, library: Any) -> bool:
        available = all(hasattr(library, name) for name in
                        ("rtlsdr_read_async", "rtlsdr_cancel_async"))
        if self._acquisition_mode == "async" and not available:
            raise RuntimeError("librtlsdr async API unavailable")
        return available and self._acquisition_mode != "sync"

    def _on_iq(self, buffer, length, _context) -> None:
        if not self._running or length == 0 or length % 2:
            return
        self._received_blocks += 1
        payload = ctypes.string_at(buffer, length)
        block = IqBlock(samples=payload,
                        center_frequency_hz=self._center_frequency_hz,
                        sample_rate_hz=self._sample_rate_hz,
                        timestamp_ns=time.monotonic_ns())
        try:
            self._queue.put_nowait(block)
        except queue.Full:
            self._dropped_blocks += 1

    def _run_async(self) -> None:
        try:
            result = self._library.rtlsdr_read_async(
                self._device, self._callback, None, 0, self._block_bytes)
            if result < 0 and self._running:
                self._worker_error = f"librtlsdr async read failed: {result}"
            elif self._running:
                self._worker_error = "librtlsdr async read exited unexpectedly"
        except Exception as exc:
            self._worker_error = str(exc)
        finally:
            self._running = False

    def read_iq(self) -> IqBlock:
        device, library = self._require_device()
        if not self._running:
            raise RuntimeError("RTL-SDR acquisition has not been started")
        if self._center_frequency_hz <= 0:
            raise RuntimeError("RTL-SDR center frequency has not been configured")

        if self._worker is not None:
            while True:
                try:
                    return self._queue.get(timeout=0.2)
                except queue.Empty:
                    if not self._running:
                        raise RuntimeError(self._worker_error or "RTL-SDR acquisition stopped")

        buffer = (ctypes.c_ubyte * self._block_bytes)()
        bytes_read = ctypes.c_int()
        timestamp_ns = time.monotonic_ns()
        self._check(
            library.rtlsdr_read_sync(
                device,
                buffer,
                self._block_bytes,
                ctypes.byref(bytes_read),
            ),
            "read IQ",
        )
        if not self._running:
            raise RuntimeError("RTL-SDR acquisition stopped while reading")
        if bytes_read.value <= 0:
            raise RuntimeError("librtlsdr returned an empty IQ block")
        if bytes_read.value % 2:
            raise RuntimeError(f"librtlsdr returned incomplete IQ pair: {bytes_read.value} bytes")

        return IqBlock(
            samples=bytes(buffer[: bytes_read.value]),
            center_frequency_hz=self._center_frequency_hz,
            sample_rate_hz=self._sample_rate_hz,
            timestamp_ns=timestamp_ns,
        )

    def _require_device(self) -> tuple[ctypes.c_void_p, Any]:
        if not self.is_connected() or self._library is None:
            raise RuntimeError("RTL-SDR source is not open")
        return self._device, self._library

    @staticmethod
    def _check(result: int, operation: str) -> None:
        if result < 0:
            raise RuntimeError(f"librtlsdr failed to {operation}: error {result}")

    @staticmethod
    def _load_library() -> ctypes.CDLL:
        name = ctypes.util.find_library("rtlsdr")
        if not name:
            raise RuntimeError(
                "Unable to find librtlsdr. Install librtlsdr or expose the ORCU-patched "
                "library through the system loader."
            )
        return ctypes.CDLL(name)

    @staticmethod
    def _configure_library(library: Any) -> None:
        """Declare the librtlsdr ABI when using a real ctypes library."""
        functions = (
            "rtlsdr_open",
            "rtlsdr_close",
            "rtlsdr_set_center_freq",
            "rtlsdr_set_sample_rate",
            "rtlsdr_set_tuner_gain_mode",
            "rtlsdr_set_tuner_gain",
            "rtlsdr_reset_buffer",
            "rtlsdr_read_sync",
        )
        for name in functions:
            if not hasattr(library, name):
                raise RuntimeError(f"librtlsdr is missing required symbol {name}")

        if isinstance(library, ctypes.CDLL) and hasattr(library, "rtlsdr_read_async"):
            library.rtlsdr_read_async.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                                   ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32]
            library.rtlsdr_read_async.restype = ctypes.c_int
            library.rtlsdr_cancel_async.argtypes = [ctypes.c_void_p]
            library.rtlsdr_cancel_async.restype = ctypes.c_int

        if isinstance(library, ctypes.CDLL) and hasattr(library, "rtlsdr_set_agc_mode"):
            library.rtlsdr_set_agc_mode.argtypes = [ctypes.c_void_p, ctypes.c_int]
            library.rtlsdr_set_agc_mode.restype = ctypes.c_int

        # Test doubles are normal Python callables and do not need ctypes metadata.
        if not isinstance(library, ctypes.CDLL):
            return

        library.rtlsdr_open.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint32]
        library.rtlsdr_open.restype = ctypes.c_int
        library.rtlsdr_close.argtypes = [ctypes.c_void_p]
        library.rtlsdr_close.restype = ctypes.c_int
        library.rtlsdr_set_center_freq.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        library.rtlsdr_set_center_freq.restype = ctypes.c_int
        library.rtlsdr_set_sample_rate.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        library.rtlsdr_set_sample_rate.restype = ctypes.c_int
        library.rtlsdr_set_tuner_gain_mode.argtypes = [ctypes.c_void_p, ctypes.c_int]
        library.rtlsdr_set_tuner_gain_mode.restype = ctypes.c_int
        library.rtlsdr_set_tuner_gain.argtypes = [ctypes.c_void_p, ctypes.c_int]
        library.rtlsdr_set_tuner_gain.restype = ctypes.c_int
        library.rtlsdr_reset_buffer.argtypes = [ctypes.c_void_p]
        library.rtlsdr_reset_buffer.restype = ctypes.c_int
        library.rtlsdr_read_sync.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
        ]
        library.rtlsdr_read_sync.restype = ctypes.c_int
