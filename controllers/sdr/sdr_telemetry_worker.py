# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Background polling for SDR telemetry without frontend dependencies."""

from __future__ import annotations

from threading import Event, Lock, Thread

from .sdr_telemetry_monitor import SDRTelemetry, SDRTelemetryMonitor


class SDRTelemetryWorker:
    """Poll an ``SDRTelemetryMonitor`` on a daemon thread.

    Frontends read ``latest`` from their own event loop. The worker never calls
    UI code, which keeps Tk and other presentation frameworks off this thread.
    """

    def __init__(self, monitor: SDRTelemetryMonitor, interval_s: float = 1.0) -> None:
        if interval_s <= 0:
            raise ValueError("interval_s must be greater than zero")
        self._monitor = monitor
        self._interval_s = interval_s
        self._include_rds = False
        self._latest = SDRTelemetry()
        self._lock = Lock()
        self._stop_event = Event()
        self._thread: Thread | None = None

    @property
    def latest(self) -> SDRTelemetry:
        with self._lock:
            return self._latest

    def set_include_rds(self, include_rds: bool) -> None:
        with self._lock:
            self._include_rds = bool(include_rds)
            if not self._include_rds and self._latest.rds != "--":
                self._latest = SDRTelemetry(
                    frequency_hz=self._latest.frequency_hz,
                    signal=self._latest.signal,
                    snr=self._latest.snr,
                    rds="--",
                )

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run, name="sdr-telemetry", daemon=True)
        self._thread.start()

    def stop(self, timeout_s: float = 2.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout_s)
        self._thread = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                include_rds = self._include_rds
            snapshot = self._monitor.read(include_rds=include_rds)
            with self._lock:
                self._latest = snapshot
            self._stop_event.wait(self._interval_s)
