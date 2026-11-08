# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Single-row HOME spectrum: decorative when idle, real analysis when active."""

import tkinter as tk

from ui.music_visualizer.music_visualizer_types import MusicCaptureState, MusicVisualizerSource


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
        active = (self._controller.capture_state() is MusicCaptureState.RUNNING
                  and self._controller.selected_source() is not MusicVisualizerSource.SIMULATED)
        frame = self._controller.latest_frame() if active else None
        spectrum = getattr(frame, "spectrum", None) if frame is not None else None
        if spectrum:
            values = tuple(max(0.0, min(1.0, float(v))) for v in spectrum)
        else:
            values = (0.24, 0.40, 0.32, 0.62, 0.85, 0.56,
                      0.96, 0.72, 0.48, 0.68, 0.38, 0.54) * 3
        # Reserve a dedicated label zone; spectrum never draws underneath text.
        label_width = min(148, max(116, width * 0.34))
        left = label_width + 8
        right = max(left + 1, width - 8)
        count = len(values)
        step = (right - left) / count
        palette = ((35, 210, 186), (66, 145, 245),
                   (132, 206, 31), (241, 90, 22))

        def color_at(position: float) -> str:
            segment = min(len(palette) - 2, int(position * (len(palette) - 1)))
            blend = position * (len(palette) - 1) - segment
            start, end = palette[segment], palette[segment + 1]
            rgb = tuple(round(a + (b - a) * blend) for a, b in zip(start, end))
            if not active:
                base = (18, 32, 44)
                rgb = tuple(round(base[i] * 0.40 + rgb[i] * 0.60) for i in range(3))
            return "#" + "".join(f"{v:02x}" for v in rgb)

        canvas.create_text(10, height / 2, anchor="w",
                           text="Music visualizer  ›", fill="#e6edf5",
                           font=("Sans", 9, "bold"))
        for index, value in enumerate(values):
            x = left + index * step
            bar_height = max(2, height * (0.72 if active else 0.48) * value)
            canvas.create_rectangle(
                x + step * 0.14, (height - bar_height) / 2,
                x + step * 0.86, (height + bar_height) / 2,
                fill=color_at(index / max(1, count - 1)), outline="",
            )

    def destroy(self):
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        super().destroy()
