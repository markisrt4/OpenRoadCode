# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Bounded Termux:API battery polling, independent of host sampling and the UI."""

import json
import math
import os
import shutil
import subprocess
import threading
import time

from ui.system_diagnostics import BatterySnapshot


class TermuxBatteryMonitor:
    """Cache Android battery readings; a slow companion app cannot stall metrics."""

    def __init__(self, *, reader=None, enabled=None, interval_seconds=30.0, monotonic=time.monotonic):
        if interval_seconds <= 0:
            raise ValueError("Battery polling interval must be positive")
        self._enabled = (bool(os.environ.get("TERMUX_VERSION")) or
                         os.environ.get("PREFIX", "").startswith("/data/data/com.termux/files/usr")) if enabled is None else enabled
        self._reader = reader or _read_battery
        self._interval = interval_seconds
        self._clock = monotonic
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._received = None
        self._sample = BatterySnapshot(state="warming_up" if self._enabled else "not_applicable",
                                       detail="Waiting for Termux:API" if self._enabled else "Termux:API battery monitoring is only used on Termux")

    def start(self):
        if not self._enabled or self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="orc-battery", daemon=True)
        self._thread.start()

    def close(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def snapshot(self):
        with self._lock:
            if self._received is not None and self._clock() - self._received > max(65, self._interval * 2):
                return BatterySnapshot(detail="Battery reading is stale")
            return self._sample

    def _run(self):
        while not self._stop.is_set():
            try:
                sample = parse_battery(self._reader())
            except (OSError, ValueError, subprocess.SubprocessError):
                sample = BatterySnapshot(detail="Termux:API unavailable; check companion app and termux-api package")
            with self._lock:
                self._sample = sample
                self._received = self._clock()
            self._stop.wait(self._interval)


def parse_battery(payload):
    """Use API degrees Celsius and percent directly, never sysfs units."""
    if not isinstance(payload, dict) or not isinstance(payload.get("present"), bool):
        return BatterySnapshot(detail="Invalid Termux:API battery response")
    if not payload["present"]:
        return BatterySnapshot(detail="Battery not present")
    def number(key, low, high):
        value = payload.get(key)
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and low <= value <= high and math.isfinite(value) else None
    def label(key):
        value = payload.get(key)
        return value[:64] if isinstance(value, str) else "UNKNOWN"
    return BatterySnapshot(state="available", temperature_c=number("temperature", -40, 150),
                           charge_percent=number("percentage", 0, 100), health=label("health"),
                           charging_state=label("status"), plugged=label("plugged"),
                           sampled_at_unix_s=time.time(), detail="Android battery via Termux:API; not CPU temperature")


def _read_battery():
    command = shutil.which("termux-battery-status")
    if command is None:
        raise FileNotFoundError("termux-battery-status")
    result = subprocess.run([command], capture_output=True, text=True, timeout=3, check=True)
    return json.loads(result.stdout)
