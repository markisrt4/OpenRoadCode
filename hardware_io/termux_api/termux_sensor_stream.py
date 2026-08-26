# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistent streaming access to one Android sensor through Termux:API."""

from __future__ import annotations

import json
import subprocess
import threading
import time

from hardware_io.imu import Vector3


class TermuxSensorStream:
    """Keep ``termux-sensor`` running and retain its latest three-axis sample."""

    def __init__(self, sensor_name: str, *, delay_ms: int = 20) -> None:
        if not sensor_name:
            raise ValueError("sensor_name must not be empty")
        if delay_ms < 0:
            raise ValueError("delay_ms must not be negative")
        self._sensor_name = sensor_name
        self._delay_ms = delay_ms
        self._process: subprocess.Popen[str] | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._sample_event = threading.Event()
        self._lock = threading.Lock()
        self._latest: Vector3 | None = None
        self._latest_at: float | None = None
        self._error: BaseException | None = None

    @property
    def is_running(self) -> bool:
        process = self._process
        return process is not None and process.poll() is None

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._sample_event.clear()
        self._error = None
        self._process = subprocess.Popen(
            ["termux-sensor", "-s", self._sensor_name, "-d", str(self._delay_ms)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._thread = threading.Thread(
            target=self._reader,
            name=f"termux-sensor-{self._sensor_name.lower().replace(' ', '-')}",
            daemon=True,
        )
        self._thread.start()

    def wait_for_sample(self, timeout_seconds: float = 5.0) -> bool:
        return self._sample_event.wait(timeout_seconds)

    def latest(self) -> tuple[Vector3, float]:
        with self._lock:
            if self._latest is None or self._latest_at is None:
                if self._error is not None:
                    raise RuntimeError(
                        f"Termux sensor stream {self._sensor_name!r} failed"
                    ) from self._error
                raise RuntimeError(
                    f"Termux sensor stream {self._sensor_name!r} has no sample yet"
                )
            return self._latest, self._latest_at

    def stop(self) -> None:
        self._stop_event.set()
        process = self._process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        self._process = None
        self._thread = None

    def _reader(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return

        decoder = json.JSONDecoder()
        buffer = ""
        try:
            while not self._stop_event.is_set():
                chunk = process.stdout.read(1)
                if chunk == "":
                    break
                buffer += chunk
                stripped = buffer.lstrip()
                if not stripped:
                    continue
                try:
                    payload, end = decoder.raw_decode(stripped)
                except json.JSONDecodeError:
                    continue

                buffer = stripped[end:]
                if not isinstance(payload, dict):
                    continue
                matching_key = next(
                    (key for key in payload if self._sensor_name.lower() in key.lower()),
                    None,
                )
                if matching_key is None:
                    continue
                entry = payload[matching_key]
                if not isinstance(entry, dict):
                    continue
                values = entry.get("values")
                if not isinstance(values, list) or len(values) < 3:
                    continue

                sample = Vector3(float(values[0]), float(values[1]), float(values[2]))
                with self._lock:
                    self._latest = sample
                    self._latest_at = time.monotonic()
                self._sample_event.set()
        except BaseException as exc:
            self._error = exc
            self._sample_event.set()
