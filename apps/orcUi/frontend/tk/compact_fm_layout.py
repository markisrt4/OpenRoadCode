"""Grid the same receiver controls in compact and spectrum layouts."""

import tkinter as tk

from ui.theme import ThemeBundle
from ui.ui_widget import UiWidget

from .automotive_radio_button import AutomotiveRadioButton


class CompactFmDial(tk.Canvas, UiWidget):
    """Show the tuned frequency on a passive FM band scale."""

    def __init__(self, parent: tk.Misc, theme: ThemeBundle) -> None:
        super().__init__(parent, height=68, highlightthickness=0, bd=0, bg=theme.ui.surface)
        self._theme = theme
        self._frequency_hz = 0
        self.bind("<Configure>", lambda _event: self._paint())

    def set_frequency(self, frequency_hz: int) -> None:
        if frequency_hz != self._frequency_hz:
            self._frequency_hz = frequency_hz
            self._paint()

    def _paint(self) -> None:
        self.delete("all")
        width = self.winfo_width() - 48
        if width <= 0:
            return
        ui = self._theme.ui
        self.create_line(24, 30, 24 + width, 30, fill=ui.border, width=2)
        for tick in range(21):
            x = 24 + width * tick / 20
            major = tick % 4 == 0
            self.create_line(x, 30, x, 43 if major else 36, fill=ui.text_muted)
            if major:
                self.create_text(
                    x, 55, text=str(88 + tick), fill=ui.text_muted, font=("Sans", 10, "bold")
                )
        if 88_000_000 <= self._frequency_hz <= 108_000_000:
            x = 24 + width * (self._frequency_hz - 88_000_000) / 20_000_000
            self.create_line(x, 10, x, 44, fill=ui.accent_primary, width=3)
            self.create_polygon(x - 6, 8, x + 6, 8, x, 17, fill=ui.accent_primary)


def place_fm_controls(
    controls: tk.Frame,
    tuning: list[AutomotiveRadioButton],
    power: AutomotiveRadioButton,
    station: tk.Frame,
    signal: tk.Label,
    heading: tk.Label,
    meter: tk.Canvas,
    *,
    compact: bool,
) -> None:
    """Move existing touch targets into the FM dashboard or receiver sidebar."""
    for column in range(5):
        active = compact or column < 2
        controls.grid_columnconfigure(
            column, weight=int(active), uniform="tuning" if active else ""
        )
    placements = (
        ((0, 0), (0, 4), (3, 0), (3, 1), (3, 3), (3, 4))
        if compact
        else ((3, 0), (3, 1), (4, 0), (4, 1), (5, 0), (5, 1))
    )
    for button, (row, column) in zip(tuning, placements, strict=True):
        button.grid_configure(row=row, column=column)
    power.grid_configure(row=5 if compact else 6, column=0, columnspan=5 if compact else 2)
    station.grid_configure(columnspan=5 if compact else 2, padx=16 if compact else 8)
    signal.grid_configure(row=4 if compact else 7)
    if compact:
        heading.grid_remove()
        meter.grid(row=4, column=2, columnspan=3, sticky="w")
    else:
        heading.grid()
        meter.grid_remove()
