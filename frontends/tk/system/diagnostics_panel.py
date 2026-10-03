# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk dashboard for computing-unit performance and rolling history."""

from __future__ import annotations

import tkinter as tk
from collections import deque

from ui.system_diagnostics import SystemDiagnosticsSnapshot
from ui.theme import ThemeBundle


class DiagnosticsPanel(tk.Frame):
    """Display host and sampler-process performance with explicit measurement scope."""

    _HISTORY_SAMPLES = 120

    def __init__(self, parent: tk.Misc, *, theme: ThemeBundle) -> None:
        self._theme = theme
        ui = theme.ui
        super().__init__(parent, bg=ui.background)

        self._values: dict[str, tk.Label] = {}
        self._last_sample_time: float | None = None
        self._history: dict[str, deque[tuple[float, float | None]]] = {
            "cpu": deque(maxlen=self._HISTORY_SAMPLES),
            "memory": deque(maxlen=self._HISTORY_SAMPLES),
            "temperature": deque(maxlen=self._HISTORY_SAMPLES),
            "process_cpu": deque(maxlen=self._HISTORY_SAMPLES),
        }
        self._graphs: dict[str, tk.Canvas] = {}
        self._identity = tk.Label(self, text="Computing unit", bg=ui.background, fg=ui.text_muted, anchor="w")
        self._identity.grid(row=0, column=0, columnspan=4, sticky="ew", padx=5, pady=4)

        for column in range(4):
            self.grid_columnconfigure(column, weight=1, uniform="metric")
        self.grid_rowconfigure(2, weight=1)

        self._metric(0, "CPU", "cpu", "cpu_detail")
        self._metric(1, "MEMORY", "memory", "memory_detail")
        self._metric(2, "THERMAL", "temperature", "thermal_detail")
        self._metric(3, "STORAGE", "storage", "storage_detail")

        trends = tk.Frame(
            self,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        trends.grid(
            row=2,
            column=0,
            columnspan=4,
            sticky="nsew",
            padx=5,
            pady=(5, 0),
        )
        trends.grid_columnconfigure(1, weight=1)

        tk.Label(
            trends,
            text="2 MINUTE TREND",
            bg=ui.surface,
            fg=ui.accent_primary,
            font=("Sans", 9, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=10,
            pady=(8, 4),
        )

        for row, (key, label) in enumerate(
            (
                ("cpu", "CPU"),
                ("memory", "RAM"),
                ("temperature", "TEMP"),
                ("process_cpu", "PROCESS"),
            ),
            start=1,
        ):
            trends.grid_rowconfigure(row, weight=1)
            tk.Label(
                trends,
                text=label,
                bg=ui.surface,
                fg=ui.text_muted,
                font=("Sans", 9, "bold"),
                width=6,
            ).grid(row=row, column=0, sticky="w", padx=(10, 4), pady=4)

            canvas = tk.Canvas(
                trends,
                height=72,
                bg=ui.surface_alt,
                highlightthickness=1,
                highlightbackground=ui.border,
            )
            canvas.grid(
                row=row,
                column=1,
                sticky="nsew",
                padx=(0, 10),
                pady=4,
            )
            self._graphs[key] = canvas
            canvas.bind("<Configure>", lambda _event, key=key: self._paint_graph(key))

        self._activity = tk.Label(self, text="", bg=ui.background, fg=ui.text_muted, anchor="w")
        self._activity.grid(row=3, column=0, columnspan=4, sticky="ew", padx=5, pady=5)
        self._process = tk.Label(self, text="", bg=ui.background, fg=ui.text_muted, anchor="w")
        self._process.grid(row=4, column=0, columnspan=4, sticky="ew", padx=5, pady=2)

    def _metric(
        self,
        column: int,
        title: str,
        key: str,
        detail_key: str,
    ) -> None:
        ui = self._theme.ui
        card = tk.Frame(
            self,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        card.grid(
            row=1,
            column=column,
            sticky="nsew",
            padx=5,
            pady=(0, 5),
        )

        tk.Label(
            card,
            text=title,
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", 9, "bold"),
        ).pack(anchor="w", padx=12, pady=(9, 2))

        value = tk.Label(
            card,
            text="--",
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", 20, "bold"),
        )
        value.pack(anchor="w", padx=12)

        detail = tk.Label(
            card,
            text="--",
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", 8),
            justify=tk.LEFT,
            anchor="w",
        )
        detail.pack(anchor="w", padx=12, pady=(1, 9))

        self._values[key] = value
        self._values[detail_key] = detail

    def apply_snapshot(self, snapshot: SystemDiagnosticsSnapshot) -> None:
        """Update current values and append the sample to rolling history."""

        self._identity.configure(text=f"{snapshot.hostname or 'Computing unit'}   {snapshot.platform}")
        self._process.configure(text=(
            f"This process (PID {snapshot.process_id or '--'}): "
            f"{_percent(snapshot.process_cpu_percent)} CPU   ·   100% = one core; excludes other processes"
        ))
        self._activity.configure(text=(
            f"Network ↓ {_rate(snapshot.network_receive_bytes_per_second)}  "
            f"↑ {_rate(snapshot.network_transmit_bytes_per_second)}     "
            f"Disk read {_rate(snapshot.disk_read_bytes_per_second)}  "
            f"write {_rate(snapshot.disk_write_bytes_per_second)}"
        ))

        self._values["cpu"].configure(text=_percent(snapshot.cpu_percent))
        core_text = ""
        if snapshot.per_core_percent:
            core_text = "  ".join(
                f"C{index}:{value:.0f}%"
                for index, value in enumerate(snapshot.per_core_percent)
            )
        frequency = (
            "-- MHz"
            if snapshot.cpu_frequency_mhz is None
            else f"{snapshot.cpu_frequency_mhz:.0f} MHz"
        )
        load = _number(snapshot.load_1m, 2)
        self._values["cpu_detail"].configure(
            text=(snapshot.cpu_unavailable_reason + "\n" if snapshot.cpu_percent is None and snapshot.cpu_unavailable_reason else "")
            + f"load {load}  {frequency}"
            + (f"\n{core_text}" if core_text else "")
        )

        self._values["memory"].configure(
            text=_percent(snapshot.memory_used_percent)
        )
        swap_text = "swap n/a"
        if snapshot.swap_total_mb is not None:
            swap_text = (
                f"swap {_number(snapshot.swap_used_mb, 0)}/"
                f"{_number(snapshot.swap_total_mb, 0)} MiB"
            )
        self._values["memory_detail"].configure(
            text=(
                f"{_number(snapshot.memory_available_mb, 0)} MiB available\n"
                f"{swap_text}"
            )
        )

        self._values["temperature"].configure(
            text=(
                "--"
                if snapshot.temperature_c is None
                else f"{snapshot.temperature_c:.0f}°C"
            )
        )
        throttle = snapshot.throttled_flags or "n/a"
        self._values["thermal_detail"].configure(
            text=(
                f"{_number(snapshot.thermal_headroom_c, 0)}°C to trip ({snapshot.thermal_zone or '--'})\n"
                f"throttle {throttle}"
            )
        )

        self._values["storage"].configure(
            text=_percent(snapshot.disk_used_percent)
        )
        self._values["storage_detail"].configure(
            text=(
                f"{_number(snapshot.disk_free_gb, 1)} GiB free\n"
                f"{_number(snapshot.disk_total_gb, 1)} GiB total ({snapshot.disk_path})"
            )
        )

        for key, value in (
            ("cpu", snapshot.cpu_percent),
            ("memory", snapshot.memory_used_percent),
            ("temperature", snapshot.temperature_c),
            ("process_cpu", snapshot.process_cpu_percent),
        ):
            if snapshot.sampled_at_unix_s is not None and snapshot.sampled_at_unix_s != self._last_sample_time:
                self._history[key].append((snapshot.sampled_at_unix_s, value))
            self._paint_graph(key)
        self._last_sample_time = snapshot.sampled_at_unix_s

    def _paint_graph(self, key: str) -> None:
        canvas = self._graphs[key]
        canvas.delete("all")

        values = tuple(self._history[key])
        if len(values) < 2:
            return

        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        ceiling = 100.0 if key != "temperature" else 120.0
        if key == "process_cpu":
            ceiling = max([100.0] + [value for _, value in values if value is not None])

        points: list[float] = []
        end_time = values[-1][0]
        for timestamp, value in values:
            if value is None:
                if len(points) >= 4:
                    canvas.create_line(*points, fill=self._theme.ui.text, width=2)
                points = []
                continue
            x = max(0.0, 1.0 - (end_time - timestamp) / 120.0) * width
            y = height - max(0.0, min(ceiling, value)) / ceiling * height
            points.extend((x, y))

        if len(points) >= 4:
            canvas.create_line(*points, fill=self._theme.ui.text, width=2)


def _percent(value: float | None) -> str:
    return "--" if value is None else f"{value:.0f}%"


def _number(value: float | None, digits: int) -> str:
    return "--" if value is None else f"{value:.{digits}f}"


def _rate(value: float | None) -> str:
    return "--" if value is None else f"{value / 1024:.0f} KiB/s"
