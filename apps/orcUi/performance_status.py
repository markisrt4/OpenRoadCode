# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Summarize observed computing-unit health for persistent shell chrome."""

from __future__ import annotations

import time
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

from ui.system_diagnostics import SystemDiagnosticsProviderIf, SystemDiagnosticsSnapshot


@dataclass(frozen=True, slots=True)
class PerformanceStatus:
    """Short text plus a semantic color; unknown data never implies failure."""

    text: str = "● SYS —"
    tone: str = "text_muted"


def performance_status(sample: SystemDiagnosticsSnapshot, *, stale: bool = False) -> PerformanceStatus:
    """Prioritize current resource pressure and observed sensor problems."""
    if stale or sample.sampled_at_unix_s is None:
        return PerformanceStatus("● SYS OLD" if stale else "● SYS —")
    conditions = []
    for name, value in (("CPU", sample.cpu_percent), ("CPU", sample.workload.cpu_capacity_percent),
                        ("RAM", sample.memory_used_percent), ("DISK", sample.disk_used_percent)):
        if value is not None and value >= 80:
            conditions.append((2 if value >= 95 else 1, name))
    headroom = sample.thermal_headroom_c
    if headroom is not None and headroom <= 10:
        conditions.append((2 if headroom <= 5 else 1, "THERMAL"))
    for sensor in sample.sensors:
        if sensor.state in {"invalid", "stale", "degraded"}:
            conditions.append((2 if sensor.state == "invalid" else 1, "SENSOR"))
    if any(service.state in {"dropping", "stopped"} for service in sample.services):
        conditions.append((2, "SERVICE"))
    if conditions:
        # Preserve the first cause at the highest severity for stable short text.
        severity, cause = max(conditions, key=lambda condition: condition[0])
        return PerformanceStatus(f"● SYS {cause}", "accent_danger" if severity == 2 else "accent_warning")
    if sample.workload.visibility != "visible":
        return PerformanceStatus("● SYS PART" if sample.workload.visibility == "partial" else "● SYS —")
    if any(value is None for value in (sample.workload.cpu_capacity_percent,
                                       sample.memory_used_percent, sample.disk_used_percent)):
        return PerformanceStatus()
    return PerformanceStatus("● SYS OK", "accent_success")


class PerformanceStatusPresenter:
    """Refresh shell status from the existing cache without another sampler."""

    def __init__(self, host, provider: SystemDiagnosticsProviderIf,
                 present: Callable[[PerformanceStatus], None], *, clock: Callable[[], float] = time.monotonic) -> None:
        self._host = host
        self._provider = provider
        self._present = present
        self._clock = clock
        self._active = False
        self._callback_id = None
        self._sample_time = None
        self._changed_at = 0.0

    def start(self) -> None:
        """Start one refresh loop on the Tk thread."""
        if self._active:
            return
        self._active = True
        self._sample_time = None
        self._changed_at = self._clock()
        self._refresh()

    def close(self) -> None:
        """Cancel the pending UI callback, tolerating an already closed host."""
        self._active = False
        if self._callback_id is not None:
            try:
                self._host.cancel_ui_callback(self._callback_id)
            except (RuntimeError, tk.TclError):
                pass
            self._callback_id = None

    def _refresh(self) -> None:
        self._callback_id = None
        if not self._active:
            return
        now = self._clock()
        try:
            sample = self._provider.snapshot()
            if sample.sampled_at_unix_s != self._sample_time:
                self._sample_time = sample.sampled_at_unix_s
                self._changed_at = now
            status = performance_status(sample, stale=now - self._changed_at > 3)
        except Exception:
            status = PerformanceStatus()
        self._present(status)
        if self._active:
            self._callback_id = self._host.schedule_ui_callback(1000, self._refresh)
