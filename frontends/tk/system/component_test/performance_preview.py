# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Preview computing-unit performance without selecting an ORC navigation entry."""

from __future__ import annotations

import tkinter as tk

from apps.orcUi.theme_runtime import theme_bundle
from frontends.tk.system.diagnostics_panel import DiagnosticsPanel
from services.common.system_performance_monitor import SystemPerformanceMonitor
from ui.theme import ThemeMode


def main() -> int:
    """Open a standalone window sampling the machine running this command."""
    root = tk.Tk()
    root.title("OpenRoadCode — Computing Unit Performance")
    root.geometry("1100x650")
    panel = DiagnosticsPanel(root, theme=theme_bundle(ThemeMode.DARK))
    panel.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
    monitor = SystemPerformanceMonitor()

    def refresh() -> None:
        panel.apply_snapshot(monitor.snapshot())
        root.after(1000, refresh)

    try:
        monitor.start()
        refresh()
        root.mainloop()
    finally:
        monitor.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
