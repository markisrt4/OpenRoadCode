# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Compact shell-owned performance HUD for touch displays."""

import tkinter as tk

from ui.system_diagnostics import SystemDiagnosticsSnapshot


def _pct(value):
    return "--" if value is None else f"{value:.0f}%"


class PerformanceOverlay:
    """Non-modal read-only HUD; the owner supplies cached snapshots."""

    def __init__(self, root: tk.Misc):
        self._root = root
        self._label = tk.Label(
            root, text="", bg="#18202b", fg="#f5f7fb",
            font=("Sans", 11, "bold"), justify=tk.LEFT,
            padx=10, pady=6, relief=tk.SOLID, bd=1,
        )
        self._visible = False

    @property
    def visible(self):
        return self._visible

    def set_visible(self, visible: bool):
        self._visible = bool(visible)
        if self._visible:
            self._label.place(relx=1, x=-12, y=64, anchor="ne")
            self._label.lift()
        else:
            self._label.place_forget()

    def update(self, sample: SystemDiagnosticsSnapshot):
        self._label.configure(
            text=f"CPU  {_pct(sample.cpu_percent)}\n"
                 f"GPU  {_pct(sample.gpu_percent)}\n"
                 f"RAM  {_pct(sample.memory_used_percent)}"
        )

    def close(self):
        self._label.destroy()
