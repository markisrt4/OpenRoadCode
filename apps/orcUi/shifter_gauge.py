# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact manual-transmission shifter gauge for ORC UI."""

from __future__ import annotations

import tkinter as tk


class ShifterGauge(tk.Canvas):
    """Show a large digital gear beside a six-speed H-pattern."""

    VALID_GEARS = {"R", "N", "1", "2", "3", "4", "5", "6"}

    def __init__(self, parent: tk.Misc, *, width: int = 390, height: int = 105) -> None:
        super().__init__(
            parent,
            width=width,
            height=height,
            bg="#090a0b",
            highlightthickness=0,
            bd=0,
        )
        self._gear: str | None = None
        self.bind("<Configure>", lambda _event: self._draw())
        self.after_idle(self._draw)

    def set_gear(self, gear: str | int | None) -> None:
        if gear is None:
            self._gear = None
        else:
            value = str(gear).strip().upper()
            self._gear = value if value in self.VALID_GEARS else None
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        border = "#626668"
        panel = "#111315"
        text = "#d9dbd9"
        muted = "#747879"
        active = "#ff3143"

        pad = max(6, int(h * 0.07))
        self.create_rectangle(
            pad,
            pad,
            w - pad,
            h - pad,
            fill=panel,
            outline=border,
            width=2,
        )

        digital_right = w * 0.34
        self.create_text(
            digital_right * 0.50,
            h * 0.22,
            text="GEAR",
            fill=text,
            font=("DejaVu Sans Condensed", max(8, int(h * 0.10)), "bold"),
        )
        self.create_text(
            digital_right * 0.50,
            h * 0.61,
            text=self._gear or "—",
            fill=active,
            font=("DejaVu Sans Mono", max(30, int(h * 0.43)), "bold"),
        )
        self.create_line(
            digital_right,
            pad * 1.7,
            digital_right,
            h - pad * 1.7,
            fill=border,
            width=2,
        )

        # Veloster six-speed pattern: R/1/3/5 across the top, 2/4/6 below.
        x_positions = [w * 0.46, w * 0.60, w * 0.74, w * 0.88]
        top_y = h * 0.31
        bottom_y = h * 0.72
        mid_y = (top_y + bottom_y) / 2

        # Draw the three forward H gates and the reverse branch.
        for x in x_positions[1:]:
            self.create_line(x, top_y, x, bottom_y, fill=muted, width=3)
        self.create_line(x_positions[1], mid_y, x_positions[3], mid_y, fill=muted, width=3)
        self.create_line(x_positions[0], top_y, x_positions[1], top_y, fill=muted, width=3)

        positions = {
            "R": (x_positions[0], top_y),
            "1": (x_positions[1], top_y),
            "2": (x_positions[1], bottom_y),
            "3": (x_positions[2], top_y),
            "4": (x_positions[2], bottom_y),
            "5": (x_positions[3], top_y),
            "6": (x_positions[3], bottom_y),
        }
        for gear, (x, y) in positions.items():
            selected = self._gear == gear
            if selected:
                radius = h * 0.105
                self.create_oval(
                    x - radius,
                    y - radius,
                    x + radius,
                    y + radius,
                    fill="#57131b",
                    outline=active,
                    width=2,
                )
            self.create_text(
                x,
                y,
                text=gear,
                fill=active if selected else text,
                font=("DejaVu Sans", max(9, int(h * 0.12)), "bold"),
            )

        # Neutral is the center cross-gate rather than another numbered position.
        neutral_x = (x_positions[2] + x_positions[1]) / 2
        if self._gear == "N":
            radius = h * 0.055
            self.create_oval(
                neutral_x - radius,
                mid_y - radius,
                neutral_x + radius,
                mid_y + radius,
                fill=active,
                outline="",
            )
