# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Low-overhead rate measurement and display for the ECU dashboard."""

import time
import tkinter as tk

from ui import UiWidget

from ui.automotive.engine_visual_state import EngineUpdateRates
from .shell_metrics import FONT_SMALL


def format_fps(render_hz: float) -> str:
    """Format the compact engine-card frame-rate indicator."""
    return f'{render_hz:.1f} FPS'


class RateCounter:
    """Count received vehicle updates and completed frames, not scheduled ticks."""

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._start = clock()
        self._updates = 0
        self._frames = 0

    def record_update(self):
        self._updates += 1

    def record_frame(self):
        self._frames += 1

    def sample(self) -> EngineUpdateRates:
        now = self._clock()
        elapsed = now-self._start
        if elapsed <= 0:
            return EngineUpdateRates()
        rates = EngineUpdateRates(self._updates/elapsed, self._frames/elapsed)
        self._start, self._updates, self._frames = now, 0, 0
        return rates


class EcuRateLabel(tk.Label, UiWidget):
    """Refresh once a second independently of animation's pause state."""

    def __init__(self, parent, *, counter, theme):
        super().__init__(parent, text='-- FPS', padx=4, pady=2,
                         bg=theme.ui.surface, fg=theme.ui.text_muted,
                         font=('Sans', FONT_SMALL))
        self._counter = counter
        self._job = self.after(1000, self._tick)
        self.bind('<Configure>', lambda event: self.configure(wraplength=max(1,event.width-8)))

    def _tick(self):
        rates = self._counter.sample()
        self.configure(text=format_fps(rates.render_hz))
        self._job = self.after(1000, self._tick)

    def destroy(self):
        self.after_cancel(self._job)
        super().destroy()
