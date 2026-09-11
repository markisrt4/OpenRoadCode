# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk dashboard for Raspberry Pi performance and capacity headroom."""

from __future__ import annotations

import tkinter as tk
from collections import deque

from ui.system_diagnostics import SystemDiagnosticsSnapshot
from ui.theme import ThemeBundle


class DiagnosticsPanel(tk.Frame):
    """Answer the practical question: how much more can this Pi handle?"""

    _HISTORY_SAMPLES = 120

    def __init__(self, parent: tk.Misc, *, theme: ThemeBundle) -> None:
        self._theme = theme
        ui = theme.ui
        super().__init__(parent, bg=ui.background)
        self._values: dict[str, tk.Label] = {}
        self._history: dict[str, deque[float]] = {
            "cpu": deque(maxlen=self._HISTORY_SAMPLES),
            "memory": deque(maxlen=self._HISTORY_SAMPLES),
            "temperature": deque(maxlen=self._HISTORY_SAMPLES),
        }
        self._graphs: dict[str, tk.Canvas] = {}

        for column in range(4):
            self.grid_columnconfigure(column, weight=1, uniform="metric")
        self.grid_rowconfigure(1, weight=1)

        self._metric(0, "CPU", "cpu", "load")
        self._metric(1, "MEMORY", "memory", "memory_detail")
        self._metric(2, "THERMAL", "temperature", "thermal_detail")
        self._metric(3, "STORAGE", "storage", "storage_detail")

        center = tk.Frame(self, bg=ui.background)
        center.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)
        center.grid_columnconfigure(0, weight=3)
        center.grid_columnconfigure(1, weight=2)
        center.grid_rowconfigure(0, weight=1)

        trends = self._panel(center, "2 MINUTE TREND")
        trends.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        for row, (key, label) in enumerate((
            ("cpu", "CPU"),
            ("memory", "RAM"),
            ("temperature", "TEMP"),
        )):
            trends.grid_rowconfigure(row + 1, weight=1)
            tk.Label(
                trends, text=label, bg=ui.surface, fg=ui.text_muted,
                font=("Sans", 8, "bold"), width=5,
            ).grid(row=row + 1, column=0, sticky="w", padx=(10, 3))
            canvas = tk.Canvas(
                trends, height=38, bg=ui.surface_alt,
                highlightthickness=1, highlightbackground=ui.border,
            )
            canvas.grid(row=row + 1, column=1, sticky="nsew", padx=(0, 10), pady=3)
            trends.grid_columnconfigure(1, weight=1)
            self._graphs[key] = canvas

        processes = self._panel(center, "TOP RESOURCE CONSUMERS")
        processes.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self._process_label = tk.Label(
            processes, text="Collecting process samples…",
            bg=ui.surface, fg=ui.text, font=("Monospace", 8),
            justify=tk.LEFT, anchor="nw",
        )
        self._process_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 10))

        capacity = self._panel(self, "SYSTEM CAPACITY")
        capacity.grid(row=2, column=0, columnspan=4, sticky="ew", padx=5, pady=(5, 0))
        capacity.grid_columnconfigure(1, weight=1)
        self._capacity_label = tk.Label(
            capacity, text="UNKNOWN", bg=ui.surface, fg=ui.text_muted,
            font=("Sans", 18, "bold"),
        )
        self._capacity_label.grid(row=1, column=0, rowspan=2, sticky="w", padx=12, pady=(0, 10))
        self._headroom_label = tk.Label(
            capacity, text="Collecting headroom…", bg=ui.surface, fg=ui.text,
            font=("Sans", 9, "bold"), anchor="w",
        )
        self._headroom_label.grid(row=1, column=1, sticky="ew", padx=12)
        self._warning_label = tk.Label(
            capacity, text="", bg=ui.surface, fg=ui.text_muted,
            font=("Sans", 8), anchor="w",
        )
        self._warning_label.grid(row=2, column=1, sticky="ew", padx=12, pady=(2, 10))

    def _metric(self, column: int, title: str, key: str, detail_key: str) -> None:
        ui = self._theme.ui
        card = tk.Frame(
            self, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border,
        )
        card.grid(row=0, column=column, sticky="nsew", padx=5, pady=(0, 5))
        tk.Label(
            card, text=title, bg=ui.surface, fg=ui.text_muted,
            font=("Sans", 9, "bold"),
        ).pack(anchor="w", padx=12, pady=(9, 2))
        value = tk.Label(
            card, text="--", bg=ui.surface, fg=ui.text,
            font=("Sans", 20, "bold"),
        )
        value.pack(anchor="w", padx=12)
        detail = tk.Label(
            card, text="--", bg=ui.surface, fg=ui.text_muted,
            font=("Sans", 8),
        )
        detail.pack(anchor="w", padx=12, pady=(1, 9))
        self._values[key] = value
        self._values[detail_key] = detail

    def _panel(self, parent: tk.Misc, title: str) -> tk.Frame:
        ui = self._theme.ui
        panel = tk.Frame(
            parent, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border,
        )
        tk.Label(
            panel, text=title, bg=ui.surface, fg=ui.accent_primary,
            font=("Sans", 9, "bold"),
        ).pack(anchor="w", padx=10, pady=(8, 2))
        return panel

    def apply_snapshot(self, snapshot: SystemDiagnosticsSnapshot) -> None:
        self._values["cpu"].configure(text=_percent(snapshot.cpu_percent))
        core_text = ""
        if snapshot.per_core_percent:
            core_text = "  " + " ".join(
                f"C{index}:{value:.0f}%" for index, value in enumerate(snapshot.per_core_percent)
            )
        freq = "" if snapshot.cpu_frequency_mhz is None else f"  {snapshot.cpu_frequency_mhz:.0f} MHz"
        self._values["load"].configure(
            text=f"load {_number(snapshot.load_1m, 2)}{freq}{core_text}"
        )

        self._values["memory"].configure(text=_percent(snapshot.memory_used_percent))
        swap = ""
        if snapshot.swap_total_mb:
            swap = f"  swap {_number(snapshot.swap_used_mb, 0)}/{_number(snapshot.swap_total_mb, 0)} MiB"
        self._values["memory_detail"].configure(
            text=f"{_number(snapshot.memory_available_mb, 0)} MiB available{swap}"
        )

        self._values["temperature"].configure(
            text="--" if snapshot.temperature_c is None else f"{snapshot.temperature_c:.0f}°C"
        )
        throttle = snapshot.throttled_flags or "n/a"
        self._values["thermal_detail"].configure(
            text=f"{_number(snapshot.thermal_headroom_c, 0)}°C headroom  throttle {throttle}"
        )

        self._values["storage"].configure(text=_percent(snapshot.disk_used_percent))
        self._values["storage_detail"].configure(
            text=f"{_number(snapshot.disk_free_gb, 1)} GiB free"
        )

        for key, value in (
            ("cpu", snapshot.cpu_percent),
            ("memory", snapshot.memory_used_percent),
            ("temperature", snapshot.temperature_c),
        ):
            if value is not None:
                self._history[key].append(value)
            self._paint_graph(key)

        if snapshot.top_processes:
            rows = ["PID     CPU    RAM      PROCESS"]
            rows.extend(
                f"{item.pid:<7} {item.cpu_percent:>4.0f}%  {item.memory_mb:>6.0f}M  {item.name[:18]}"
                for item in snapshot.top_processes
            )
            self._process_label.configure(text="\n".join(rows))
        else:
            self._process_label.configure(text="Collecting process samples…")

        ui = self._theme.ui
        status_color = {
            "HEALTHY": ui.accent_success,
            "MODERATE": ui.accent_warning,
            "LIMITED": ui.accent_danger,
        }.get(snapshot.capacity_status, ui.text_muted)
        self._capacity_label.configure(text=snapshot.capacity_status, fg=status_color)
        self._headroom_label.configure(
            text="  •  ".join(snapshot.capacity_reasons) or "Headroom unavailable"
        )
        self._warning_label.configure(
            text="  •  ".join(snapshot.warnings) if snapshot.warnings else "No current resource-pressure warnings",
            fg=ui.accent_danger if snapshot.warnings else ui.text_muted,
        )

    def _paint_graph(self, key: str) -> None:
        canvas = self._graphs[key]
        canvas.delete("all")
        values = tuple(self._history[key])
        if len(values) < 2:
            return
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        ceiling = 100.0 if key != "temperature" else 90.0
        points: list[float] = []
        for index, value in enumerate(values):
            x = index * width / max(1, self._HISTORY_SAMPLES - 1)
            y = height - max(0.0, min(ceiling, value)) / ceiling * height
            points.extend((x, y))
        canvas.create_line(*points, fill=self._theme.ui.text, width=2)


def _percent(value: float | None) -> str:
    return "--" if value is None else f"{value:.0f}%"


def _number(value: float | None, digits: int) -> str:
    return "--" if value is None else f"{value:.{digits}f}"
