# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable Tk system performance and diagnostics panel."""

from __future__ import annotations

import tkinter as tk

from ui.system_diagnostics import SystemDiagnosticsSnapshot
from ui.theme import ThemeBundle


class DiagnosticsPanel(tk.Frame):
    """Render system health as glanceable metrics and diagnostic details."""

    def __init__(self, parent: tk.Misc, *, theme: ThemeBundle) -> None:
        self._theme = theme
        ui = theme.ui
        super().__init__(parent, bg=ui.background)

        self._metric_values: dict[str, tk.Label] = {}
        self._detail_values: dict[str, tk.Label] = {}

        self.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="metric")
        self.grid_rowconfigure(1, weight=1)

        self._build_metric(0, "CPU", "cpu")
        self._build_metric(1, "MEMORY", "memory")
        self._build_metric(2, "STORAGE", "storage")
        self._build_metric(3, "TEMPERATURE", "temperature")

        details = tk.Frame(
            self,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        details.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)
        details.grid_columnconfigure(0, weight=1)
        details.grid_columnconfigure(1, weight=1)

        self._build_detail_group(
            details,
            0,
            "OPENROADCODE PROCESS",
            (
                ("Memory", "process_memory"),
                ("Threads", "process_threads"),
                ("Uptime", "uptime"),
            ),
        )
        self._build_detail_group(
            details,
            1,
            "HOST",
            (
                ("Host", "hostname"),
                ("Platform", "platform"),
                ("Kernel", "kernel"),
                ("Python", "python"),
            ),
        )

        warning_frame = tk.Frame(
            self,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        warning_frame.grid(row=2, column=0, columnspan=4, sticky="ew", padx=5, pady=(5, 0))
        warning_frame.grid_columnconfigure(1, weight=1)
        tk.Label(
            warning_frame,
            text="HEALTH",
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", 9, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(12, 8), pady=10)
        self._health_label = tk.Label(
            warning_frame,
            text="Collecting diagnostics…",
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", 10, "bold"),
            anchor="w",
        )
        self._health_label.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=10)

    def _build_metric(self, column: int, title: str, key: str) -> None:
        ui = self._theme.ui
        card = tk.Frame(
            self,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        card.grid(row=0, column=column, sticky="nsew", padx=5, pady=(0, 5))
        tk.Label(
            card,
            text=title,
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", 9, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 3))
        value = tk.Label(
            card,
            text="--",
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", 20, "bold"),
        )
        value.pack(anchor="w", padx=12)
        self._metric_values[key] = value
        if key == "cpu":
            secondary = tk.Label(
                card,
                text="Load --",
                bg=ui.surface,
                fg=ui.text_muted,
                font=("Sans", 8),
            )
            secondary.pack(anchor="w", padx=12, pady=(2, 10))
            self._metric_values["load"] = secondary
        elif key == "memory":
            secondary = tk.Label(
                card,
                text="-- / -- MiB",
                bg=ui.surface,
                fg=ui.text_muted,
                font=("Sans", 8),
            )
            secondary.pack(anchor="w", padx=12, pady=(2, 10))
            self._metric_values["memory_detail"] = secondary
        elif key == "storage":
            secondary = tk.Label(
                card,
                text="-- GiB free",
                bg=ui.surface,
                fg=ui.text_muted,
                font=("Sans", 8),
            )
            secondary.pack(anchor="w", padx=12, pady=(2, 10))
            self._metric_values["storage_detail"] = secondary
        else:
            tk.Label(
                card,
                text="CPU / SoC",
                bg=ui.surface,
                fg=ui.text_muted,
                font=("Sans", 8),
            ).pack(anchor="w", padx=12, pady=(2, 10))

    def _build_detail_group(
        self,
        parent: tk.Misc,
        column: int,
        title: str,
        rows: tuple[tuple[str, str], ...],
    ) -> None:
        ui = self._theme.ui
        group = tk.Frame(parent, bg=ui.surface)
        group.grid(row=0, column=column, sticky="nsew", padx=14, pady=12)
        group.grid_columnconfigure(1, weight=1)
        tk.Label(
            group,
            text=title,
            bg=ui.surface,
            fg=ui.accent_primary,
            font=("Sans", 9, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        for row, (label_text, key) in enumerate(rows, start=1):
            tk.Label(
                group,
                text=label_text,
                bg=ui.surface,
                fg=ui.text_muted,
                font=("Sans", 9),
            ).grid(row=row, column=0, sticky="w", padx=(0, 16), pady=2)
            value = tk.Label(
                group,
                text="--",
                bg=ui.surface,
                fg=ui.text,
                font=("Monospace", 9, "bold"),
                anchor="w",
            )
            value.grid(row=row, column=1, sticky="ew", pady=2)
            self._detail_values[key] = value

    def apply_snapshot(self, snapshot: SystemDiagnosticsSnapshot) -> None:
        """Paint one diagnostics sample."""

        self._metric_values["cpu"].configure(text=_percent(snapshot.cpu_percent))
        self._metric_values["load"].configure(
            text=f"Load {_number(snapshot.load_1m, 2)}"
            + ("" if snapshot.cpu_count is None else f" / {snapshot.cpu_count} CPUs")
        )
        self._metric_values["memory"].configure(text=_percent(snapshot.memory_used_percent))
        self._metric_values["memory_detail"].configure(
            text=f"{_number(snapshot.memory_used_mb, 0)} / {_number(snapshot.memory_total_mb, 0)} MiB"
        )
        self._metric_values["storage"].configure(text=_percent(snapshot.disk_used_percent))
        self._metric_values["storage_detail"].configure(
            text=f"{_number(snapshot.disk_free_gb, 1)} / {_number(snapshot.disk_total_gb, 1)} GiB free/total"
        )
        self._metric_values["temperature"].configure(
            text="--" if snapshot.temperature_c is None else f"{snapshot.temperature_c:.0f}°C"
        )

        self._detail_values["process_memory"].configure(
            text="--" if snapshot.process_rss_mb is None else f"{snapshot.process_rss_mb:.1f} MiB RSS"
        )
        self._detail_values["process_threads"].configure(
            text="--" if snapshot.process_threads is None else str(snapshot.process_threads)
        )
        self._detail_values["uptime"].configure(text=_duration(snapshot.uptime_seconds))
        self._detail_values["hostname"].configure(text=snapshot.hostname or "--")
        self._detail_values["platform"].configure(text=snapshot.platform_name or "--")
        self._detail_values["kernel"].configure(text=snapshot.kernel_release or "--")
        self._detail_values["python"].configure(text=snapshot.python_version or "--")

        ui = self._theme.ui
        if snapshot.warnings:
            self._health_label.configure(
                text="  •  ".join(snapshot.warnings),
                fg=ui.accent_danger,
            )
        else:
            self._health_label.configure(
                text="All sampled metrics are within normal thresholds",
                fg=ui.accent_success,
            )


def _percent(value: float | None) -> str:
    return "--" if value is None else f"{value:.0f}%"


def _number(value: float | None, digits: int) -> str:
    return "--" if value is None else f"{value:.{digits}f}"


def _duration(seconds: float | None) -> str:
    if seconds is None:
        return "--"
    total = max(0, int(seconds))
    days, remainder = divmod(total, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"
