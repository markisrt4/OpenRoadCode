# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Diagnostics tabs prioritizing ORC workload and observed sensor telemetry."""

from __future__ import annotations

import tkinter as tk
from collections import deque

from ui.system_diagnostics import SystemDiagnosticsSnapshot
from ui.theme import ThemeBundle
from .diagnostics_tabs import DiagnosticsTabs
from .diagnostics_table import DiagnosticsTable
from .system_metrics_panel import SystemMetricsPanel, pressure_color
from ui.ui_widget import UiWidget


class DiagnosticsPanel(tk.Frame, UiWidget):
    """Show workload attribution first; keep host and telemetry health separate."""

    def __init__(self, parent: tk.Misc, *, theme: ThemeBundle) -> None:
        super().__init__(parent, bg=theme.ui.background)
        self._theme = theme
        self._last_sample_time = None
        self._history = deque(maxlen=120)
        ui = theme.ui
        tabs = DiagnosticsTabs(self, theme=theme)
        tabs.pack(fill=tk.BOTH, expand=True)
        workload = tk.Frame(tabs, bg=ui.background)
        system = SystemMetricsPanel(tabs, theme=theme)
        sensors = tk.Frame(tabs, bg=ui.background)
        tabs.add(workload, text="ORC workload")
        tabs.add(system, text="System")
        tabs.add(sensors, text="Sensor telemetry")
        services = tk.Frame(tabs, bg=ui.background)
        tabs.add(services, text="Services")
        self._system = system

        self._cpu = self._label(workload, "Waiting for ORC process samples", 16)
        self._memory = self._label(workload, "", 12)
        self._visibility = self._label(workload, "", 10)
        self._cpu_note = self._label(workload, "CPU 100% = one core. RSS counts shared pages per process; PSS apportions shared memory.", 10)
        self._process_table = self._table(workload, (
            ("name", "Process", 290), ("pid", "PID", 60), ("state", "State", 55),
            ("cpu", "CPU %", 80), ("rss", "RSS MiB", 85), ("pss", "PSS MiB", 85),
            ("threads", "Threads", 65), ("read", "Read KiB/s", 90), ("write", "Write KiB/s", 90),
        ), visible=("name", "cpu", "rss", "pss"))
        self._process_table.tag_configure("diagnostics", foreground=ui.text_muted)
        self._process_table.tag_configure("workload", foreground=ui.accent_primary)
        self._label(workload, "ORC workload CPU • last 2 minutes • 100% = one core", 10)
        self._trend = tk.Canvas(workload, height=80, bg=ui.surface, highlightthickness=0)
        self._trend.pack(fill=tk.X, padx=6, pady=4)
        self._trend.bind("<Configure>", lambda _event: self._paint_trend())
        self._process_detail = self._label(workload, "Select a process for its full name, PID, threads and disk activity", 10)
        self._process_detail.configure(wraplength=900)
        self._process_rows = {}
        self._process_table.bind("<<TreeviewSelect>>", self._show_process_detail)

        self._sensor_status = self._label(sensors, "Sensor monitoring not started", 13)
        self._label(sensors, "Telemetry freshness, not hardware self-test. Not observed may mean disabled or unconfigured.", 10)
        self._sensor_table = self._table(sensors, (
            ("name", "Stream", 160), ("source", "Source", 200), ("state", "State", 100),
            ("age", "Received age", 100), ("sample", "Advance age", 100),
            ("rate", "Rate Hz", 80), ("invalid", "Invalid count", 100),
        ), visible=("name", "source", "state", "age", "rate"))
        for state, color in (("streaming", ui.accent_success), ("stale", ui.accent_warning),
                             ("degraded", ui.accent_warning), ("invalid", ui.accent_danger),
                             ("not_observed", ui.text_muted), ("unavailable", ui.text_muted)):
            self._sensor_table.tag_configure(state, foreground=color)
        legend = tk.Frame(sensors, bg=ui.background)
        legend.pack(fill=tk.X, padx=6)
        for text, color in (("Streaming", ui.accent_success), ("Stale / degraded", ui.accent_warning),
                            ("Invalid", ui.accent_danger), ("Unknown", ui.text_muted)):
            tk.Label(legend, text="● " + text, bg=ui.background, fg=color).pack(side=tk.LEFT, padx=(0, 16))
        self._sensor_detail = self._label(sensors, "Select a stream to see its status detail and stale threshold", 11)
        self._sensor_detail.configure(wraplength=900)
        self._sensor_rows = {}
        self._sensor_table.bind("<<TreeviewSelect>>", self._show_sensor_detail)

        self._service_status = self._label(services, "Waiting for service socket samples", 12)
        self._service_status.configure(wraplength=900)
        self._label(services, "TCP/UDP socket health · RX/TX are payload KiB/s · queues are occupancy · -- means unavailable", 10)
        self._service_table = self._table(services, (
            ("name", "Service", 190), ("pid", "PID", 60), ("process", "Process", 100), ("protocol", "Protocol", 65),
            ("state", "Sockets", 125), ("local", "Local endpoint", 180), ("remote", "Peer", 180),
            ("rx", "RX KiB/s", 90), ("tx", "TX KiB/s", 90),
            ("rxq", "RX queue B", 90), ("txq", "TX queue B", 90), ("drops", "UDP drops", 90),
        ), visible=("name", "process", "protocol", "state", "rx", "tx"))
        for state, color in (("connected", ui.accent_success), ("listening", ui.accent_success),
                             ("connecting", ui.accent_warning), ("closing", ui.accent_warning),
                             ("dropping", ui.accent_danger), ("stopped", ui.accent_danger),
                             ("bound", ui.accent_primary), ("closed", ui.text_muted),
                             ("unknown", ui.text_muted), ("no_socket", ui.text_muted),
                             ("not_observed", ui.text_muted), ("unavailable", ui.text_muted)):
            self._service_table.tag_configure(state, foreground=color)
        self._service_detail = self._label(services, "Select an endpoint for health and bandwidth details. UDP rates are unavailable without service counters.", 10)
        self._service_detail.configure(wraplength=900)
        self._service_rows = {}
        self._service_table.bind("<<TreeviewSelect>>", self._show_service_detail)

    def _label(self, parent, text: str, size: int):
        label = tk.Label(parent, text=text, anchor="w", justify=tk.LEFT,
                         bg=self._theme.ui.background, fg=self._theme.ui.text, font=("Sans", size))
        label.pack(fill=tk.X, padx=6, pady=4)
        return label

    def _table(self, parent, columns, *, visible):
        table = DiagnosticsTable(parent, theme=self._theme, columns=columns, visible=visible)
        table.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        return table

    def apply_snapshot(self, snapshot: SystemDiagnosticsSnapshot) -> None:
        """Refresh tables using cached samples without sampling on the Tk thread."""
        self._system.apply_snapshot(snapshot)
        self._service_status.configure(text=snapshot.service_monitor_status)
        self._service_rows = {str(index): row for index, row in enumerate(snapshot.services)}
        service_selection = self._service_table.selection()
        self._service_table.delete(*self._service_table.get_children())
        for key, row in self._service_rows.items():
            self._service_table.insert("", tk.END, iid=key, values=(
                row.name, row.pid or "--", row.process_state.title().replace("_", " "), row.protocol, row.state.title().replace("_", " "), row.local_endpoint, row.remote_endpoint,
                _format(row.receive_bytes_per_second, 1024), _format(row.transmit_bytes_per_second, 1024),
                row.receive_queue_bytes if row.receive_queue_bytes is not None else "--",
                row.transmit_queue_bytes if row.transmit_queue_bytes is not None else "--",
                row.udp_drops if row.udp_drops is not None else "--",
            ), tags=(row.state,))
        if service_selection and service_selection[0] in self._service_rows:
            self._service_table.selection_set(service_selection[0])
            self._show_service_detail()
        work = snapshot.workload
        self._process_rows = {str(row.pid): row for row in work.processes}
        self._cpu_note.configure(text=(
            f"100% CPU = one logical core · {snapshot.cpu_count or '--'} logical CPUs detected. "
            "RSS counts shared pages; PSS apportions them."
        ))
        self._cpu.configure(fg=pressure_color(self._theme.ui, work.cpu_capacity_percent))
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
        self._visibility.configure(text=f"{work.visibility.upper()}: {work.detail}",
                                   fg=self._theme.ui.accent_warning if work.visibility == "partial" else self._theme.ui.text_muted)
        selected = self._process_table.selection()
        current = set()
        for index, process in enumerate(work.processes):
            row_id = str(process.pid)
            current.add(row_id)
            values = (
                _process_name(process.name) + (" · diagnostics" if process.category == "diagnostics" else ""),
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
            self._show_process_detail()
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
                sensor.name, sensor.source or "--", sensor.state.title().replace("_", " "),
                _format(sensor.last_received_age_seconds) + " s",
                _format(sensor.last_sample_age_seconds) + " s",
                _format(sensor.message_rate_hz), sensor.invalid_message_count,
            ), tags=(sensor.state,))
        if sensor_selection and sensor_selection[0] in self._sensor_rows:
            self._sensor_table.selection_set(sensor_selection[0])
            self._show_sensor_detail()

    def _show_process_detail(self, _event=None) -> None:
        selected = self._process_table.selection()
        if selected and selected[0] in self._process_rows:
            row = self._process_rows[selected[0]]
            self._process_detail.configure(text=(
                f"{row.name} · PID {row.pid} · state {row.state} · {row.thread_count} threads · "
                f"read {_format(row.read_bytes_per_second, 1024)} KiB/s · write {_format(row.write_bytes_per_second, 1024)} KiB/s"))

    def _show_service_detail(self, _event=None) -> None:
        selected = self._service_table.selection()
        if selected and selected[0] in self._service_rows:
            row = self._service_rows[selected[0]]
            self._service_detail.configure(text=(f"PID {row.pid or '--'} · {row.local_endpoint} → {row.remote_endpoint} · "
                f"queues RX {_format(row.receive_queue_bytes)} B / TX {_format(row.transmit_queue_bytes)} B · "
                f"UDP drops {row.udp_drops if row.udp_drops is not None else '--'} · ") + row.detail + (
                f" Current drops: {_format(row.drops_per_second)}/s" if row.protocol == "UDP" else ""))

    def _show_sensor_detail(self, _event=None) -> None:
        selected = self._sensor_table.selection()
        if selected and selected[0] in self._sensor_rows:
            sensor = self._sensor_rows[selected[0]]
            self._sensor_detail.configure(text=(f"{sensor.source or '--'} · {sensor.detail} · "
                f"sample advance age {_format(sensor.last_sample_age_seconds)} s · "
                f"invalid {sensor.invalid_message_count} · stale after {sensor.stale_after_seconds:g} s"))

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
                    canvas.create_line(*points, fill=self._theme.ui.accent_primary, width=2)
                points = []
                continue
            points.extend((max(0, 1 - (end - timestamp) / 120) * width, height - value / ceiling * height))
        if len(points) >= 4:
            canvas.create_line(*points, fill=self._theme.ui.accent_primary, width=2)
        canvas.create_text(5, 5, text=f"0–{ceiling:.0f}%", anchor="nw", fill=self._theme.ui.text_muted)


def _format(value, divisor=1) -> str:
    return "--" if value is None else f"{value / divisor:.1f}"


def _process_name(name):
    for token, label in (("service_manager", "Service manager"), ("navigation_service", "Navigation"),
                         ("automotive_service", "Automotive"), ("broker", "Message broker"),
                         ("apps.orcUi", "ORC UI"), ("android_sensor", "Android sensors")):
        if token in name:
            return label
    return name
