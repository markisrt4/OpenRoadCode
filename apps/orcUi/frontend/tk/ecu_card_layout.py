# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Responsive telemetry card layout for the ECU screen."""

import tkinter as tk

from .shell_metrics import FONT_SMALL, FONT_BODY


def fit_ecu_card(body: tk.Frame, width: int, *, field_labels, labels, bars) -> None:
    """Keep numbers readable before spending narrow card width on bars."""
    compact = width < 320
    short_labels = {
        "commanded": "Target λ", "measured": "Actual λ", "load": "Load",
        "boost": "Boost", "throttle": "Throttle", "timing": "Advance",
        "fuel_status": "Fuel", "mixture_status": "Tracking", "ignition_status": "Timing",
    }
    for key, label in field_labels.items():
        if label.master is body:
            label.configure(text=short_labels.get(key, label._full_text) if compact else label._full_text)
    for key, value in labels.items():
        if value.master is not body:
            continue
        if key.endswith("_mode"):
            value.configure(font=("Sans", FONT_SMALL if compact else 15, "bold"),
                            wraplength=max(1, width-8))
        elif key.endswith("_status"):
            value.configure(font=("Sans", FONT_SMALL, "bold"),
                            wraplength=max(1, width-65))
        else:
            value.configure(font=("Sans", FONT_SMALL if compact else FONT_BODY, "bold"))
    for canvas in bars.values():
        if canvas.master is body:
            if compact:
                canvas.grid_remove()
            else:
                canvas.grid()
    body.grid_columnconfigure(2, weight=0 if compact else 2)

