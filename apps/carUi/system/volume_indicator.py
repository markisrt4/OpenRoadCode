from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk


@dataclass(frozen=True, slots=True)
class VolumeIndicatorStyle:
    """Define dimensions and colors for the system volume indicator."""
    background: str
    active: str
    inactive: str
    muted: str
    bar_width: int
    base_height: int
    height_step: int
    bar_gap: int
    anchor: str
    side: str


class VolumeIndicator(tk.Frame):
    """Render volume level and mute state as a vertical bar graph."""
    def __init__(
        self,
        parent: tk.Widget,
        *,
        steps: int,
        initial_level: int,
        initial_muted: bool,
        style: VolumeIndicatorStyle,
    ) -> None:
        super().__init__(parent, bg=style.background)
        self._steps = max(1, steps)
        self._level = max(0, min(initial_level, self._steps))
        self._muted = initial_muted
        self._style = style
        self._bars: list[tk.Frame] = []
        self._build()

    def set_level(self, level: int) -> None:
        self._level = max(0, min(level, self._steps))
        self._render()

    def set_muted(self, muted: bool) -> None:
        self._muted = muted
        self._render()

    def _render(self) -> None:
        for index, bar in enumerate(self._bars):
            if self._muted:
                color = self._style.muted
            elif index < self._level:
                color = self._style.active
            else:
                color = self._style.inactive
            bar.configure(
                bg=color
            )

    def _build(self) -> None:
        for index in range(self._steps):
            bar = tk.Frame(
                self,
                bg=self._style.inactive,
                width=self._style.bar_width,
                height=self._style.base_height + index * self._style.height_step,
            )
            bar.pack(
                side=self._style.side,
                padx=self._style.bar_gap,
                anchor=self._style.anchor,
            )
            self._bars.append(bar)
        self.set_level(self._level)
