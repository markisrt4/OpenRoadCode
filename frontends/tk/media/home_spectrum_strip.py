# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Small real-audio spectrum beneath Home album artwork."""
from collections.abc import Callable
import tkinter as tk

from ui.music_visualizer.home_spectrum_ui_if import HomeSpectrumFeedIf
from ui.ui_widget import UiWidget


class HomeSpectrumStrip(tk.Canvas, UiWidget):
    """Render cached bands only while actual capture supplies fresh audio."""

    def __init__(self, parent: tk.Misc, *, feed: HomeSpectrumFeedIf,
                 background: str, on_open: Callable[[], None]) -> None:
        super().__init__(parent, width=48, height=22, bg=background,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._feed = feed
        self._attached = False
        self._closed = False
        self._tick_id: str | None = None
        self.bind("<Button-1>", lambda _event: on_open())
        self._host = parent
        self._tick_id = self.after(66, self._paint)

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
        if state and state.active and state.bands:
            self.pack(pady=(2, 0))
            count = len(state.bands)
            colors = ("#21b8a6", "#28b6c6", "#37a7e0", "#7293e8")
            for index in range(8):
                values = state.bands[index * count // 8:max(index * count // 8 + 1, (index + 1) * count // 8)]
                height = max(1, round(max(values, default=0.0) * 20))
                self.create_rectangle(index * 6, 22 - height, index * 6 + 4, 22,
                                      fill=colors[index // 2], outline="")
        else:
            self.pack_forget()
        self._tick_id = self.after(66, self._paint)

    def destroy(self) -> None:
        if not self._closed:
            self._closed = True
            if self._tick_id is not None:
                self.after_cancel(self._tick_id)
            self._detach()
        super().destroy()
