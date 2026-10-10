# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk dashboard for computing-unit performance and rolling history."""

from __future__ import annotations

import tkinter as tk
from collections import deque

from ui.system_diagnostics import SystemDiagnosticsSnapshot
from ui.theme import ThemeBundle


class SystemMetricsPanel(tk.Frame):
    """Display host and sampler-process performance with explicit measurement scope."""

    _HISTORY_SAMPLES = 120

    def __init__(self, parent: tk.Misc, *, theme: ThemeBundle) -> None:
        self._theme = theme
        ui = theme.ui
        super().__init__(parent, bg=ui.background)

        self._values: dict[str, tk.Label] = {}
        self._last_snapshot = None
        self._last_sample_time: float | None = None
        self._history: dict[str, deque[tuple[float, float | None]]] = {
            "cpu": deque(maxlen=self._HISTORY_SAMPLES),
            "memory": deque(maxlen=self._HISTORY_SAMPLES),
            "temperature": deque(maxlen=self._HISTORY_SAMPLES),
            "process_cpu": deque(maxlen=self._HISTORY_SAMPLES),
        }
        self._graph_colors = {"cpu": ui.accent_primary, "memory": ui.accent_success,
                              "temperature": ui.accent_warning, "process_cpu": ui.text_muted}
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
        trends.grid_columnconfigure((0, 1), weight=1, uniform="trend")
        trends.grid_rowconfigure((0, 1), weight=1, uniform="trend")

        for index, (key, label) in enumerate(
            (("cpu", "CPU"), ("memory", "RAM"),
             ("temperature", "TEMP"), ("process_cpu", "PROCESS CPU"))
        ):
            card = tk.Frame(trends, bg=ui.surface)
            card.grid(row=index // 2, column=index % 2,
                      sticky="nsew", padx=8, pady=3)
            card.grid_columnconfigure(0, weight=1)
            card.grid_rowconfigure(1, weight=1)
            tk.Label(card, text=label + " · 2 MIN", bg=ui.surface,
                     fg=self._graph_colors[key], font=("Sans", 9, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", pady=(0, 3))
            canvas = tk.Canvas(card, height=60, width=120,
                               bg=ui.surface_alt, highlightthickness=1,
                               highlightbackground=ui.border)
            canvas.grid(row=1, column=0, sticky="nsew")
            self._graphs[key] = canvas
            canvas.bind("<Configure>", lambda _event, key=key: self._paint_graph(key))

        self._process = tk.Label(self, text="", bg=ui.background, fg=ui.text_muted, anchor="w")
        self._process.grid(row=3, column=0, columnspan=4, sticky="ew", padx=5, pady=2)
        self._battery = tk.Label(self, text="", bg=ui.surface, fg=ui.text_muted,
                                 anchor="w", font=("Sans", 11, "bold"), padx=10, pady=6)
        self._battery.grid(row=4, column=0, columnspan=4, sticky="ew", padx=5, pady=4)

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

        title_label = tk.Label(
            card,
            text=title + (" ▾" if key == "temperature" else ""),
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", 9, "bold"),
        )
        title_label.pack(anchor="w", padx=12, pady=(9, 2))
        if key == "temperature":
            title_label.configure(fg=ui.accent_primary, cursor="hand2")
            title_label.bind("<Button-1>", self._show_thermal_sources)

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

        self._last_snapshot = snapshot
        battery = snapshot.battery
        if battery.state == "available":
            self._battery.configure(text=(f"BATTERY  {_number(battery.temperature_c, 1)}°C · "
                f"{_number(battery.charge_percent, 0)}% · {battery.health} · "
                f"{battery.charging_state} · {battery.plugged}"),
                fg=(self._theme.ui.accent_success if battery.health == "GOOD" else
                    self._theme.ui.accent_danger if battery.health in {"OVERHEAT", "DEAD", "OVER_VOLTAGE", "UNSPECIFIED_FAILURE"} else
                    self._theme.ui.text_muted if battery.health == "UNKNOWN" else self._theme.ui.accent_warning))
        else:
            self._battery.configure(text=f"BATTERY  -- · {battery.detail}", fg=self._theme.ui.text_muted)
        if battery.state == "not_applicable":
            self._battery.grid_remove()
        else:
            self._battery.grid()
        self._identity.configure(text=f"{snapshot.hostname or 'Computing unit'}   {snapshot.platform}")
        self._process.configure(text=(
            f"This process (PID {snapshot.process_id or '--'}): "
            f"{_percent(snapshot.process_cpu_percent)} CPU   ·   100% = one core; excludes other processes"
        ))

        ui = self._theme.ui
        for key, percent in (("cpu", snapshot.cpu_percent), ("memory", snapshot.memory_used_percent),
                             ("storage", snapshot.disk_used_percent)):
            self._values[key].configure(fg=pressure_color(ui, percent))
        headroom = snapshot.thermal_headroom_c
        self._values["temperature"].configure(fg=(ui.text_muted if headroom is None else
            ui.accent_danger if headroom <= 5 else ui.accent_warning if headroom <= 10 else ui.accent_success))
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
            + f"{snapshot.cpu_count or '--'} logical CPUs · load {load}  {frequency}"
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
                f"{snapshot.thermal_source_type or snapshot.thermal_zone or 'source unidentified'}\n"
                f"{_number(snapshot.thermal_headroom_c, 0)}°C to trip · {snapshot.thermal_zone or '--'}\n"
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

    def _show_thermal_sources(self, _event=None) -> None:
        sample = self._last_snapshot
        if sample is None:
            return
        ui = self._theme.ui
        window = tk.Toplevel(self)
        window.title("Reported thermal sources")
        window.configure(bg=ui.background)
        window.geometry("700x420")
        tk.Label(window, text=sample.thermal_detail + "\nRaw vendor readings are not whole-phone temperatures.",
                 bg=ui.background, fg=ui.text, justify=tk.LEFT, wraplength=660).pack(fill=tk.X, padx=12, pady=12)
        frame = tk.Frame(window, bg=ui.background)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        text = tk.Text(frame, bg=ui.surface, fg=ui.text, insertbackground=ui.text,
                       font=("Monospace", 10), relief=tk.FLAT, wrap=tk.NONE,
                       bd=0, highlightthickness=0)
        scroll = tk.Scrollbar(frame, command=text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text.configure(yscrollcommand=scroll.set)
        text.pack(fill=tk.BOTH, expand=True)
        for row in sample.thermal_sources:
            text.insert(tk.END, f"{row.zone}  {row.source_type}  {row.temperature_c:.1f}°C  trip {_number(row.trip_c, 1)}°C\n")
        if not sample.thermal_sources:
            text.insert(tk.END, "No readable sources\n")
        text.configure(state=tk.DISABLED)

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
                    canvas.create_line(*points, fill=self._graph_colors[key], width=2)
                points = []
                continue
            x = max(0.0, 1.0 - (end_time - timestamp) / 120.0) * width
            y = height - max(0.0, min(ceiling, value)) / ceiling * height
            points.extend((x, y))

        if len(points) >= 4:
            canvas.create_line(*points, fill=self._graph_colors[key], width=2)


def _percent(value: float | None) -> str:
    return "--" if value is None else f"{value:.0f}%"


def _number(value: float | None, digits: int) -> str:
    return "--" if value is None else f"{value:.{digits}f}"


def _rate(value: float | None) -> str:
    return "--" if value is None else f"{value / 1024:.0f} KiB/s"


def pressure_color(ui, percent: float | None) -> str:
    """Color normalized resource usage; missing measurements remain neutral."""
    if percent is None:
        return ui.text_muted
    return ui.accent_danger if percent >= 95 else ui.accent_warning if percent >= 80 else ui.accent_success
