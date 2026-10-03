# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Sample host performance independently of HTTP clients and UI refreshes."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import asdict

from controllers.system.system_diagnostics_controller import SystemDiagnosticsController
from ui.system_diagnostics import SystemDiagnosticsSnapshot


class SystemPerformanceMonitor:
    """Own one sampler, a bounded history, and a read-only snapshot cache."""

    def __init__(
        self, controller: SystemDiagnosticsController | None = None, *,
        interval_seconds: float = 1.0, history_samples: int = 120,
    ) -> None:
        if interval_seconds <= 0 or history_samples <= 0:
            raise ValueError("Sampling interval and history size must be positive")
        self._controller = controller or SystemDiagnosticsController()
        self._interval = interval_seconds
        self._history: deque[SystemDiagnosticsSnapshot] = deque(maxlen=history_samples)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._sample_monotonic: float | None = None
        self._error: str | None = None

    def start(self) -> None:
        """Start sampling in a worker; never perform firmware calls on the UI thread."""
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="orc-performance", daemon=True)
        self._thread.start()

    def close(self) -> None:
        """Stop the owned worker before releasing its sampler."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def snapshot(self) -> SystemDiagnosticsSnapshot:
        """Return the cached sample immediately, or an empty sample during warmup."""
        with self._lock:
            return self._history[-1] if self._history else SystemDiagnosticsSnapshot()

    def history(self) -> tuple[SystemDiagnosticsSnapshot, ...]:
        """Return samples in acquisition order for local trend views."""
        with self._lock:
            return tuple(self._history)

    def payload(self) -> dict[str, object]:
        """Return versioned SI telemetry and two minutes of bounded history."""
        with self._lock:
            history = tuple(self._history)
            age = None if self._sample_monotonic is None else time.monotonic() - self._sample_monotonic
            error = self._error
        return {
            "version": 1,
            "sample_interval_seconds": self._interval,
            "sample_age_seconds": age,
            "error": error,
            "snapshot": _wire_snapshot(history[-1]) if history else None,
            "history": [{
                "sampled_at_unix_s": sample.sampled_at_unix_s,
                "cpu_percent": sample.cpu_percent,
                "process_cpu_percent": sample.process_cpu_percent,
                "memory_used_percent": sample.memory_used_percent,
                "temperature_c": sample.temperature_c,
            } for sample in history],
        }

    def _run(self) -> None:
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                sample = self._controller.snapshot()
            except Exception as error:
                with self._lock:
                    self._error = type(error).__name__
            else:
                with self._lock:
                    self._history.append(sample)
                    self._sample_monotonic = time.monotonic()
                    self._error = None
            self._stop.wait(max(0.0, self._interval - (time.monotonic() - started)))


def _wire_snapshot(snapshot: SystemDiagnosticsSnapshot) -> dict[str, object]:
    """Convert the recovered presentation contract's MiB/GiB/MHz to SI units."""
    values = asdict(snapshot)
    for name in ("memory_available_mb", "memory_used_mb", "memory_total_mb", "swap_used_mb", "swap_total_mb"):
        value = values.pop(name)
        values[name.removesuffix("_mb") + "_bytes"] = None if value is None else round(value * 1024**2)
    for name in ("disk_free_gb", "disk_total_gb"):
        value = values.pop(name)
        values[name.removesuffix("_gb") + "_bytes"] = None if value is None else round(value * 1024**3)
    frequency = values.pop("cpu_frequency_mhz")
    values["cpu_frequency_hz"] = None if frequency is None else frequency * 1_000_000
    return values
