# SPDX-License-Identifier: MIT
"""Quiet fuel strip for the Home cockpit, using supplied presentation values."""

import math
import tkinter as tk

from ui import UiWidget
from ui.theme import UiTheme


class HomeFuelBar(tk.Canvas, UiWidget):
    def __init__(self, parent: tk.Misc, *, theme: UiTheme) -> None:
        super().__init__(parent, bg=theme.surface_alt, height=64, width=250,
                         bd=0, highlightthickness=0)
        self._ui = theme
        self._value: float | None = None
        self.bind("<Configure>", lambda _event: self._draw())

    def set_value(self, value: float | None) -> None:
        self._value = None if value is None or not math.isfinite(value) else max(0.0, min(100.0, value))
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        if width < 30 or height < 30:
            return
        ui, value = self._ui, self._value
        color = ui.text_muted if value is None else ui.accent_danger if value <= 12.5 else (
            ui.accent_warning if value <= 25 else ui.accent_success)
        self.create_text(12, height * 0.32, text="FUEL", anchor="w",
                         fill=ui.text_muted, font=("Sans", 10, "bold"))
        self.create_text(width - 12, height * 0.32, text="—" if value is None else f"{value:.0f}%",
                         anchor="e", fill=color, font=("Sans", 16, "bold"))
        top, bottom = height * 0.66, height * 0.80
        self.create_rectangle(12, top, width - 12, bottom,
                              fill=ui.control_background, outline="")
        if value is not None and value > 0:
            self.create_rectangle(12, top, 12 + (width - 24) * value / 100, bottom,
                                  fill=color, outline="")
