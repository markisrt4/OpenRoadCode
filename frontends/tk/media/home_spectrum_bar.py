# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Single-row HOME spectrum: decorative when idle, real analysis when active."""

import tkinter as tk

from ui.music_visualizer.music_visualizer_types import MusicCaptureState


class HomeSpectrumBar(tk.Frame):
    HEIGHT = 48

    def __init__(self, parent, *, controller, theme_bundle, on_open):
        ui = theme_bundle().ui
        super().__init__(parent, bg=ui.surface, height=self.HEIGHT)
        self.grid_propagate(False)
        self._controller = controller
        self._on_open = on_open
        self._job = None
        self._canvas = tk.Canvas(self, bg=ui.surface, bd=0, highlightthickness=0,
                                 height=self.HEIGHT, cursor="hand2")
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas.bind("<Button-1>", lambda _event: self._on_open())
        self._canvas.bind("<Configure>", lambda _event: self._paint())
        self._poll()

    def _poll(self):
        self._paint()
        self._job = self.after(100, self._poll)

    def _paint(self):
        canvas = self._canvas
        if not canvas.winfo_exists():
            return
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 2 or height < 2:
            return
        active = self._controller.capture_state() is MusicCaptureState.RUNNING
        frame = self._controller.latest_frame() if active else None
        spectrum = getattr(frame, "spectrum", None) if frame is not None else None
        if spectrum:
            values = tuple(max(0.0, min(1.0, float(v))) for v in spectrum)
        else:
            values = (0.24, 0.40, 0.32, 0.62, 0.85, 0.56,
                      0.96, 0.72, 0.48, 0.68, 0.38, 0.54) * 3
        count = len(values)
        step = width / count
        colors = ("#23d2ba", "#4291f5", "#a568ee")
        for index, value in enumerate(values):
            x = index * step
            color = colors[min(2, index * 3 // count)]
            bar_height = max(2, height * 0.78 * value)
            if not active:
                bar_height *= 0.70
            canvas.create_rectangle(x + step * 0.16, (height - bar_height) / 2,
                                    x + step * 0.84, (height + bar_height) / 2,
                                    fill=color if active else "#34516b", outline="")
        if not active:
            canvas.create_text(12, height / 2, anchor="w",
                               text="Music visualizer  ›", fill="#e6edf5",
                               font=("Sans", 10, "bold"))

    def destroy(self):
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        super().destroy()
