# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Card-wide real-audio spectrum and explicit Home capture controls."""
from collections.abc import Callable
import tkinter as tk

from ui.music_visualizer.home_spectrum_ui_if import HomeSpectrumFeedIf
from ui.ui_widget import UiWidget
from .spectrum_illustration import paint_spectrum_illustration


class HomeSpectrumStrip(tk.Canvas, UiWidget):
    """Render cached bands only while actual capture supplies fresh audio."""

    def __init__(self, parent: tk.Misc, *, feed: HomeSpectrumFeedIf,
                 background: str, on_open: Callable[[], None]) -> None:
        super().__init__(parent, width=1, height=68, bg=background,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._feed = feed
        self._attached = False
        self._closed = False
        self._tick_id: str | None = None
        self.bind("<Button-1>", lambda _event: on_open())
        self._host = parent
        self._button = tk.Button(self, text="▶ Spectrum", command=self._request_toggle,
            font=("Sans", 9, "bold"), bg=background, fg="#28b6c6",
            activebackground=background, activeforeground="#7293e8",
            relief=tk.FLAT, bd=0, highlightthickness=0, padx=3)
        self._button.place(relx=1.0, rely=0.5, anchor="e", width=108, height=68)
        self._running = False
        self._tick_id = self.after(66, self._paint)

    def set_background(self, background: str) -> None:
        """Follow shell theme colors without changing capture state."""
        self.configure(bg=background)
        self._button.configure(bg=background, activebackground=background)

    def _request_toggle(self) -> None:
        if self._closed:
            return
        if self._running:
            self._feed.request_stop_spectrum()
        else:
            self._feed.request_start_spectrum()

    def _detach(self) -> None:
        if self._attached:
            self._attached = False
            self._feed.detach_home()

    def _paint(self) -> None:
        if self._closed:
            return
        visible = bool(self._host.winfo_viewable())
        if visible and not self._attached:
            self._attached = True
            self._feed.attach_home()
        elif not visible:
            self._detach()
        state = self._feed.read_spectrum() if self._attached else None
        self.delete("all")
        self._running = bool(state and state.running)
        self._button.configure(text="Starting…" if state and state.busy and not self._running
            else "Stopping…" if state and state.busy else "■ Spectrum" if self._running
            else "▶ Spectrum", state=tk.DISABLED if state and state.busy else tk.NORMAL)
        canvas_height = max(2, self.winfo_height())
        width = max(1, self.winfo_width() - 112)
        if state and state.active and state.bands:
            count = len(state.bands)
            colors = ("#21b8a6", "#28b6c6", "#37a7e0", "#7293e8")
            bars = min(24, max(1, width // 5))
            for index in range(bars):
                values = state.bands[index * count // bars:max(index * count // bars + 1, (index + 1) * count // bars)]
                height = max(1, round(max(values, default=0.0) * (canvas_height - 4)))
                x = index * width / bars
                self.create_rectangle(x, canvas_height - 2 - height,
                                      x + max(1, width / bars - 2), canvas_height - 2,
                                      fill=colors[min(3, index * 4 // bars)], outline="")
        else:
            paint_spectrum_illustration(
                self, width, canvas_height, muted_fraction=0.0,
            )
        self._tick_id = self.after(66, self._paint)

    def destroy(self) -> None:
        if not self._closed:
            self._closed = True
            if self._tick_id is not None:
                self.after_cancel(self._tick_id)
            self._detach()
        super().destroy()
