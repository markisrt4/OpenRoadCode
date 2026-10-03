# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Diagnostics tabs prioritizing ORC workload and observed sensor telemetry."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from collections import deque

from ui.system_diagnostics import SystemDiagnosticsSnapshot
from ui.theme import ThemeBundle
from .system_metrics_panel import SystemMetricsPanel


class DiagnosticsPanel(tk.Frame):
    """Show workload attribution first; keep host and telemetry health separate."""

    def __init__(self, parent: tk.Misc, *, theme: ThemeBundle) -> None:
        super().__init__(parent, bg=theme.ui.background)
        self._theme = theme
        self._last_sample_time = None
        self._history = deque(maxlen=120)
        ui = theme.ui
        style = ttk.Style(self)
        style.configure("Diagnostics.TNotebook", background=ui.background, borderwidth=0)
        style.configure("Diagnostics.TNotebook.Tab", padding=(16, 8))
        style.configure("Diagnostics.Treeview", background=ui.surface, fieldbackground=ui.surface,
                        foreground=ui.text, rowheight=27)
        tabs = ttk.Notebook(self, style="Diagnostics.TNotebook")
        tabs.pack(fill=tk.BOTH, expand=True)
        workload = tk.Frame(tabs, bg=ui.background)
        system = SystemMetricsPanel(tabs, theme=theme)
        sensors = tk.Frame(tabs, bg=ui.background)
        tabs.add(workload, text="ORC workload")
        tabs.add(system, text="System")
        tabs.add(sensors, text="Sensor telemetry")
        self._system = system

        self._cpu = self._label(workload, "Waiting for ORC process samples", 16)
        self._memory = self._label(workload, "", 12)
        self._visibility = self._label(workload, "", 10)
        self._label(workload, "CPU 100% = one core. RSS counts shared pages per process; PSS apportions shared memory.", 10)
        self._process_table = self._table(workload, (
            ("name", "Process", 290), ("pid", "PID", 60), ("state", "State", 55),
            ("cpu", "CPU %", 80), ("rss", "RSS MiB", 85), ("pss", "PSS MiB", 85),
            ("threads", "Threads", 65), ("read", "Read KiB/s", 90), ("write", "Write KiB/s", 90),
        ))
        self._process_table.tag_configure("diagnostics", foreground=ui.text_muted)
        self._label(workload, "ORC workload CPU • last 2 minutes • 100% = one core", 10)
        self._trend = tk.Canvas(workload, height=80, bg=ui.surface, highlightthickness=0)
        self._trend.pack(fill=tk.X, padx=6, pady=4)
        self._trend.bind("<Configure>", lambda _event: self._paint_trend())

        self._sensor_status = self._label(sensors, "Sensor monitoring not started", 13)
        self._label(sensors, "Telemetry freshness, not hardware self-test. Not observed may mean disabled or unconfigured.", 10)
        self._sensor_table = self._table(sensors, (
            ("name", "Stream", 160), ("source", "Source", 200), ("state", "State", 100),
            ("age", "Received age", 100), ("sample", "Advance age", 100),
            ("rate", "Rate Hz", 80), ("invalid", "Invalid count", 100),
        ))
        self._sensor_detail = self._label(sensors, "Select a stream to see its status detail and stale threshold", 11)
        self._sensor_rows = {}
        self._sensor_table.bind("<<TreeviewSelect>>", self._show_sensor_detail)

    def _label(self, parent, text: str, size: int):
        label = tk.Label(parent, text=text, anchor="w", justify=tk.LEFT,
                         bg=self._theme.ui.background, fg=self._theme.ui.text, font=("Sans", size))
        label.pack(fill=tk.X, padx=6, pady=4)
        return label

    def _table(self, parent, columns):
        frame = tk.Frame(parent, bg=self._theme.ui.background)
        frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        tree = ttk.Treeview(frame, columns=[column[0] for column in columns],
                            show="headings", style="Diagnostics.Treeview", height=8)
        for key, title, width in columns:
            tree.heading(key, text=title)
            tree.column(key, width=width, minwidth=45, anchor="w" if key in ("name", "source") else "e")
        vertical = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        horizontal = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        return tree

    def apply_snapshot(self, snapshot: SystemDiagnosticsSnapshot) -> None:
        """Refresh tables using cached samples without sampling on the Tk thread."""
        self._system.apply_snapshot(snapshot)
        work = snapshot.workload
        self._cpu.configure(text=(
            f"ORC workload: {_format(work.cpu_percent)}% CPU · "
            f"{_format(work.cpu_capacity_percent)}% of CPU capacity · {work.process_count} processes"
        ))
        self._memory.configure(text=(
            f"RSS sum {_format(work.rss_bytes, 1024**2)} MiB · "
            f"PSS {_format(work.pss_bytes, 1024**2)} MiB · "
            f"Disk read {_format(work.read_bytes_per_second, 1024)} KiB/s · "
            f"write {_format(work.write_bytes_per_second, 1024)} KiB/s"
        ))
        self._visibility.configure(text=f"{work.visibility.upper()}: {work.detail}")
        selected = self._process_table.selection()
        current = set()
        for index, process in enumerate(work.processes):
            row_id = str(process.pid)
            current.add(row_id)
            values = (
                process.name + (" [diagnostics]" if process.category == "diagnostics" else ""),
                process.pid, process.state, _format(process.cpu_percent),
                _format(process.rss_bytes, 1024**2), _format(process.pss_bytes, 1024**2),
                process.thread_count, _format(process.read_bytes_per_second, 1024),
                _format(process.write_bytes_per_second, 1024),
            )
            if self._process_table.exists(row_id):
                self._process_table.item(row_id, values=values, tags=(process.category,))
                self._process_table.move(row_id, "", index)
            else:
                self._process_table.insert("", index, iid=row_id, values=values, tags=(process.category,))
        for row_id in self._process_table.get_children():
            if row_id not in current:
                self._process_table.delete(row_id)
        if selected and selected[0] in current:
            self._process_table.selection_set(selected[0])
        if snapshot.sampled_at_unix_s is not None and snapshot.sampled_at_unix_s != self._last_sample_time:
            self._history.append((snapshot.sampled_at_unix_s, work.cpu_percent))
        self._last_sample_time = snapshot.sampled_at_unix_s
        self._paint_trend()

        self._sensor_status.configure(text=f"Sensor telemetry monitor: {snapshot.sensor_monitor_status}")
        self._sensor_rows = {str(index): row for index, row in enumerate(snapshot.sensors)}
        sensor_selection = self._sensor_table.selection()
        self._sensor_table.delete(*self._sensor_table.get_children())
        for key, sensor in self._sensor_rows.items():
            self._sensor_table.insert("", tk.END, iid=key, values=(
                sensor.name, sensor.source or "--", sensor.state.upper(),
                _format(sensor.last_received_age_seconds) + " s",
                _format(sensor.last_sample_age_seconds) + " s",
                _format(sensor.message_rate_hz), sensor.invalid_message_count,
            ))
        if sensor_selection and sensor_selection[0] in self._sensor_rows:
            self._sensor_table.selection_set(sensor_selection[0])
            self._show_sensor_detail()

    def _show_sensor_detail(self, _event=None) -> None:
        selected = self._sensor_table.selection()
        if selected and selected[0] in self._sensor_rows:
            sensor = self._sensor_rows[selected[0]]
            self._sensor_detail.configure(text=f"{sensor.detail} · stale after {sensor.stale_after_seconds:g} s")

    def _paint_trend(self) -> None:
        canvas = self._trend
        canvas.delete("all")
        if len(self._history) < 2:
            return
        width, height = max(1, canvas.winfo_width()), max(1, canvas.winfo_height())
        ceiling = max([100.0] + [value for _, value in self._history if value is not None])
        end = self._history[-1][0]
        points = []
        for timestamp, value in self._history:
            if value is None:
                if len(points) >= 4:
                    canvas.create_line(*points, fill=self._theme.ui.text, width=2)
                points = []
                continue
            points.extend((max(0, 1 - (end - timestamp) / 120) * width, height - value / ceiling * height))
        if len(points) >= 4:
            canvas.create_line(*points, fill=self._theme.ui.text, width=2)
        canvas.create_text(5, 5, text=f"0–{ceiling:.0f}%", anchor="nw", fill=self._theme.ui.text_muted)


def _format(value, divisor=1) -> str:
    return "--" if value is None else f"{value / divisor:.1f}"
